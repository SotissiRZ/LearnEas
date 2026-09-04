import json
import logging
import urllib.error
import urllib.request
from decimal import Decimal

from django.conf import settings
from django.db import IntegrityError
from django.utils import timezone

from apps.accounts.models import PlatformSettings
from .models import NotificationPreference, WhatsAppDelivery, EmailDelivery
from .email_services import queue_email_event
from .serializers import normalize_whatsapp_phone

logger = logging.getLogger(__name__)


_EVENT_PREF_FIELD = {
    WhatsAppDelivery.EventType.PAYMENT: "whatsapp_payment_enabled",
    WhatsAppDelivery.EventType.LIVE: "whatsapp_live_enabled",
    WhatsAppDelivery.EventType.INACTIVITY: "whatsapp_inactivity_enabled",
    WhatsAppDelivery.EventType.CERTIFICATE: "whatsapp_certificate_enabled",
}

_EVENT_TEMPLATE_FIELD = {
    WhatsAppDelivery.EventType.PAYMENT: "whatsapp_payment_template_name",
    WhatsAppDelivery.EventType.LIVE: "whatsapp_live_template_name",
    WhatsAppDelivery.EventType.INACTIVITY: "whatsapp_inactivity_template_name",
    WhatsAppDelivery.EventType.CERTIFICATE: "whatsapp_certificate_template_name",
    WhatsAppDelivery.EventType.TEST: "whatsapp_test_template_name",
}


def whatsapp_runtime_status():
    config = PlatformSettings.load()
    dry_run = bool(getattr(settings, "WHATSAPP_DRY_RUN", True))
    env_enabled = bool(getattr(settings, "WHATSAPP_ENABLED", False))
    phone_id = bool(getattr(settings, "WHATSAPP_PHONE_NUMBER_ID", ""))
    token = bool(getattr(settings, "WHATSAPP_ACCESS_TOKEN", ""))
    app_secret = bool(getattr(settings, "WHATSAPP_APP_SECRET", ""))
    return {
        "platform_enabled": bool(config.whatsapp_enabled),
        "environment_enabled": env_enabled,
        "dry_run": dry_run,
        "credentials_configured": bool(phone_id and token),
        "webhook_signature_configured": app_secret,
        "ready": bool(config.whatsapp_enabled and env_enabled and (dry_run or (phone_id and token))),
        "graph_api_version": getattr(settings, "WHATSAPP_GRAPH_API_VERSION", "v25.0"),
    }


def _event_allowed(preference, event_type):
    field = _EVENT_PREF_FIELD.get(event_type)
    return bool(not field or getattr(preference, field, False))


def queue_whatsapp_event(*, user, event_type, event_key, variables, metadata=None):
    """Crée une notification transactionnelle idempotente et la délègue à Celery.

    L'absence de consentement est un arrêt normal : aucune ligne n'est créée afin de ne pas
    transformer le journal d'envoi en base de prospection involontaire.
    """
    config = PlatformSettings.load()
    if not (config.whatsapp_enabled and getattr(settings, "WHATSAPP_ENABLED", False)):
        return None
    try:
        preference = user.notification_preferences
    except NotificationPreference.DoesNotExist:
        return None
    if not preference.whatsapp_opt_in or not preference.whatsapp_phone or not _event_allowed(preference, event_type):
        return None
    template_field = _EVENT_TEMPLATE_FIELD[event_type]
    template_name = str(getattr(config, template_field, "") or "").strip()
    if not template_name:
        logger.warning("Template WhatsApp manquant pour %s", event_type)
        return None
    try:
        delivery, created = WhatsAppDelivery.objects.get_or_create(
            event_key=event_key,
            defaults={
                "user": user,
                "recipient": preference.whatsapp_phone,
                "event_type": event_type,
                "template_name": template_name,
                "language_code": config.whatsapp_template_language or "fr",
                "variables": [str(v)[:1024] for v in variables],
                "metadata": metadata or {},
            },
        )
    except IntegrityError:
        delivery = WhatsAppDelivery.objects.filter(event_key=event_key).first()
        created = False
    if delivery and created:
        try:
            from .tasks import send_whatsapp_delivery
            send_whatsapp_delivery.delay(delivery.id)
        except Exception:
            # Une panne Redis ne doit jamais annuler un paiement ou une délivrance de certificat.
            logger.exception("Impossible d'enfiler la notification WhatsApp %s", delivery.id)
    return delivery


def create_admin_test_delivery(*, user, phone):
    import uuid

    config = PlatformSettings.load()
    normalized = normalize_whatsapp_phone(phone)
    delivery = WhatsAppDelivery.objects.create(
        user=user,
        recipient=normalized,
        event_type=WhatsAppDelivery.EventType.TEST,
        event_key=f"test:{uuid.uuid4().hex}",
        template_name=config.whatsapp_test_template_name or "hello_world",
        language_code=config.whatsapp_template_language or "en_US",
        variables=[],
        metadata={"requested_by_admin": user.id},
    )
    try:
        from .tasks import send_whatsapp_delivery
        send_whatsapp_delivery.delay(delivery.id)
    except Exception:
        logger.exception("Impossible d'enfiler le test WhatsApp %s", delivery.id)
    return delivery


def send_delivery(delivery_id):
    delivery = WhatsAppDelivery.objects.filter(pk=delivery_id).first()
    if not delivery or delivery.status not in {WhatsAppDelivery.Status.QUEUED, WhatsAppDelivery.Status.FAILED}:
        return delivery
    config = PlatformSettings.load()
    if not (config.whatsapp_enabled and getattr(settings, "WHATSAPP_ENABLED", False)):
        delivery.status = WhatsAppDelivery.Status.SKIPPED
        delivery.error = "WhatsApp désactivé dans la configuration KalanPro."
        delivery.save(update_fields=["status", "error"])
        return delivery
    if getattr(settings, "WHATSAPP_DRY_RUN", True):
        delivery.status = WhatsAppDelivery.Status.SIMULATED
        delivery.sent_at = timezone.now()
        delivery.provider_response = {"dry_run": True, "template": delivery.template_name, "variables": delivery.variables}
        delivery.error = ""
        delivery.save(update_fields=["status", "sent_at", "provider_response", "error"])
        return delivery

    phone_number_id = str(getattr(settings, "WHATSAPP_PHONE_NUMBER_ID", "") or "").strip()
    token = str(getattr(settings, "WHATSAPP_ACCESS_TOKEN", "") or "").strip()
    version = str(getattr(settings, "WHATSAPP_GRAPH_API_VERSION", "v25.0") or "v25.0").strip()
    if not phone_number_id or not token:
        delivery.status = WhatsAppDelivery.Status.FAILED
        delivery.failed_at = timezone.now()
        delivery.error = "Identifiants Meta WhatsApp Cloud API incomplets."
        delivery.save(update_fields=["status", "failed_at", "error"])
        return delivery

    body_parameters = [{"type": "text", "text": str(value)[:1024]} for value in delivery.variables]
    template = {
        "name": delivery.template_name,
        "language": {"code": delivery.language_code},
    }
    if body_parameters:
        template["components"] = [{"type": "body", "parameters": body_parameters}]
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": delivery.recipient.lstrip("+"),
        "type": "template",
        "template": template,
    }
    url = f"https://graph.facebook.com/{version}/{phone_number_id}/messages"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=int(getattr(settings, "WHATSAPP_HTTP_TIMEOUT", 15))) as response:
            response_payload = json.loads(response.read().decode("utf-8") or "{}")
        provider_id = str(((response_payload.get("messages") or [{}])[0]).get("id") or "")
        delivery.status = WhatsAppDelivery.Status.SENT
        delivery.sent_at = timezone.now()
        delivery.provider_message_id = provider_id
        delivery.provider_response = response_payload
        delivery.error = ""
        delivery.save(update_fields=["status", "sent_at", "provider_message_id", "provider_response", "error"])
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8")
            parsed = json.loads(detail)
        except Exception:
            parsed = {"detail": str(exc)}
        delivery.status = WhatsAppDelivery.Status.FAILED
        delivery.failed_at = timezone.now()
        delivery.provider_response = parsed
        delivery.error = str(parsed)[:3000]
        delivery.save(update_fields=["status", "failed_at", "provider_response", "error"])
        logger.warning("Meta WhatsApp a refusé l'envoi %s: %s", delivery.id, delivery.error)
    except Exception as exc:
        delivery.status = WhatsAppDelivery.Status.FAILED
        delivery.failed_at = timezone.now()
        delivery.error = str(exc)[:3000]
        delivery.save(update_fields=["status", "failed_at", "error"])
        logger.exception("Échec réseau WhatsApp pour %s", delivery.id)
    return delivery


def queue_payment_confirmation(order_id):
    from apps.payments.models import Order

    order = Order.objects.select_related("user").filter(pk=order_id).first()
    if not order or order.status != Order.Status.PAID:
        return None
    name = order.user.first_name or order.user.get_full_name() or order.user.username
    amount = f"{Decimal(order.total_amount):f} {order.currency}"
    wa = queue_whatsapp_event(
        user=order.user,
        event_type=WhatsAppDelivery.EventType.PAYMENT,
        event_key=f"payment:{order.id}",
        variables=[name, order.invoice_number, amount],
        metadata={"order_id": order.id},
    )
    email = queue_email_event(
        user=order.user,
        event_type=EmailDelivery.EventType.PAYMENT,
        event_key=f"email:payment:{order.id}",
        subject=f"Paiement confirmé · {order.invoice_number}",
        context={
            "eyebrow": "Paiement confirmé",
            "title": "Votre paiement a bien été reçu",
            "greeting": f"Bonjour {name},",
            "intro": "Votre commande KalanPro est confirmée. Vos contenus et services associés sont maintenant disponibles dans votre espace.",
            "details": [
                {"label": "Référence", "value": order.invoice_number},
                {"label": "Montant", "value": amount},
                {"label": "Statut", "value": "Payé"},
            ],
            "cta_label": "Accéder à mon espace",
            "cta_url": f"{settings.FRONTEND_URL.rstrip('/')}/dashboard",
            "footer_note": "Conservez cet email comme confirmation de votre transaction.",
        },
        metadata={"order_id": order.id},
    )
    return {"whatsapp": wa, "email": email}


def queue_certificate_ready(certificate_id):
    from apps.enrollments.models import Certificate

    certificate = Certificate.objects.select_related("user").filter(pk=certificate_id).first()
    if not certificate:
        return None
    name = certificate.user.first_name or certificate.student_name or certificate.user.username
    verify_url = f"{settings.FRONTEND_URL.rstrip('/')}/certificates/verify/{certificate.verification_code}"
    wa = queue_whatsapp_event(
        user=certificate.user,
        event_type=WhatsAppDelivery.EventType.CERTIFICATE,
        event_key=f"certificate:{certificate.id}:{certificate.verification_code}",
        variables=[name, certificate.content_title, verify_url],
        metadata={"certificate_id": certificate.id},
    )
    email = queue_email_event(
        user=certificate.user,
        event_type=EmailDelivery.EventType.CERTIFICATE,
        event_key=f"email:certificate:{certificate.id}:{certificate.verification_code}",
        subject=f"Votre certificat KalanPro est disponible · {certificate.content_title}",
        context={
            "eyebrow": "Certification",
            "title": "Votre certificat est prêt",
            "greeting": f"Félicitations {name} !",
            "intro": f"Vous avez satisfait aux critères de réussite pour « {certificate.content_title} ». Votre certificat KalanPro est désormais vérifiable en ligne.",
            "details": [
                {"label": "Formation", "value": certificate.content_title},
                {"label": "Code de vérification", "value": certificate.verification_code},
            ],
            "cta_label": "Voir et vérifier le certificat",
            "cta_url": verify_url,
            "footer_note": "Le lien de vérification peut être partagé avec un recruteur, un client ou une entreprise.",
        },
        metadata={"certificate_id": certificate.id},
    )
    return {"whatsapp": wa, "email": email}
