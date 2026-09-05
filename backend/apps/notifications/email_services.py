import json
import logging
import urllib.error
import urllib.request
from html import unescape
from re import sub

from django.conf import settings
from django.db import IntegrityError
from django.template.loader import render_to_string
from django.utils import timezone

from apps.accounts.models import PlatformSettings
from .models import EmailDelivery, NotificationPreference

logger = logging.getLogger(__name__)

_EMAIL_PREF_FIELD = {
    EmailDelivery.EventType.PAYMENT: "email_payment_enabled",
    EmailDelivery.EventType.LIVE: "email_live_enabled",
    EmailDelivery.EventType.INACTIVITY: "email_inactivity_enabled",
    EmailDelivery.EventType.CERTIFICATE: "email_certificate_enabled",
    EmailDelivery.EventType.RECRUITMENT: "email_recruitment_enabled",
}


def resend_runtime_status():
    config = PlatformSettings.load()
    env_enabled = bool(getattr(settings, "RESEND_ENABLED", False))
    dry_run = bool(getattr(settings, "RESEND_DRY_RUN", True))
    api_key = bool(str(getattr(settings, "RESEND_API_KEY", "") or "").strip())
    return {
        "platform_enabled": bool(config.resend_enabled),
        "environment_enabled": env_enabled,
        "dry_run": dry_run,
        "credentials_configured": api_key,
        "ready": bool(config.resend_enabled and env_enabled and (dry_run or api_key)),
        "from": f"{config.resend_from_name} <{config.resend_from_email}>",
        "reply_to": config.resend_reply_to,
    }


def _email_allowed(user, event_type):
    if not user:
        return True
    preference, _ = NotificationPreference.objects.get_or_create(user=user)
    if not preference.email_enabled:
        return False
    field = _EMAIL_PREF_FIELD.get(event_type)
    return bool(not field or getattr(preference, field, True))


def queue_email_event(*, user=None, recipient=None, event_type, event_key, subject, context, metadata=None, force=False):
    config = PlatformSettings.load()
    if not (config.resend_enabled and getattr(settings, "RESEND_ENABLED", False)):
        return None
    email = str(recipient or getattr(user, "email", "") or "").strip().lower()
    if not email:
        return None
    if not force and not _email_allowed(user, event_type):
        return None
    try:
        delivery, created = EmailDelivery.objects.get_or_create(
            event_key=event_key,
            defaults={
                "user": user,
                "recipient": email,
                "event_type": event_type,
                "subject": str(subject)[:255],
                "template_key": "transactional",
                "template_context": context or {},
                "metadata": metadata or {},
            },
        )
    except IntegrityError:
        delivery = EmailDelivery.objects.filter(event_key=event_key).first()
        created = False
    if delivery and created:
        try:
            from .tasks import send_email_delivery
            send_email_delivery.delay(delivery.id)
        except Exception:
            logger.exception("Impossible d'enfiler l'email Resend %s", delivery.id)
            # Les emails de sécurité/invitation ne doivent pas dépendre exclusivement de Redis.
            if force:
                try:
                    send_email(delivery.id)
                except Exception:
                    logger.exception("Échec du fallback synchrone Resend %s", delivery.id)
    return delivery


def _plain_text_from_context(context):
    parts = []
    if context.get("greeting"):
        parts.append(str(context["greeting"]))
    if context.get("intro"):
        parts.append(str(context["intro"]))
    for item in context.get("details") or []:
        label = str(item.get("label") or "").strip()
        value = str(item.get("value") or "").strip()
        if label or value:
            parts.append(f"{label}: {value}" if label else value)
    if context.get("body"):
        parts.append(str(context["body"]))
    if context.get("cta_url"):
        parts.append(f"{context.get('cta_label') or 'Ouvrir KalanPro'}: {context['cta_url']}")
    parts.append("\nKalanPro — Apprenez. Évoluez. Trouvez un emploi.")
    return "\n\n".join(parts)


def render_email(delivery):
    config = PlatformSettings.load()
    context = dict(delivery.template_context or {})
    context.update({
        "site_name": config.site_name or "KalanPro",
        "support_email": config.support_email,
        "recipient": delivery.recipient,
        "subject": delivery.subject,
        "frontend_url": settings.FRONTEND_URL.rstrip("/"),
    })
    html = render_to_string("notifications/email/transactional.html", context)
    return html, _plain_text_from_context(context)


def send_email(delivery_id):
    delivery = EmailDelivery.objects.filter(pk=delivery_id).first()
    if not delivery or delivery.status not in {EmailDelivery.Status.QUEUED, EmailDelivery.Status.FAILED}:
        return delivery
    config = PlatformSettings.load()
    if not (config.resend_enabled and getattr(settings, "RESEND_ENABLED", False)):
        delivery.status = EmailDelivery.Status.SKIPPED
        delivery.error = "Email Resend désactivé dans la configuration KalanPro."
        delivery.save(update_fields=["status", "error"])
        return delivery

    html, text = render_email(delivery)
    if getattr(settings, "RESEND_DRY_RUN", True):
        delivery.status = EmailDelivery.Status.SIMULATED
        delivery.sent_at = timezone.now()
        delivery.provider_response = {
            "dry_run": True,
            "subject": delivery.subject,
            "html_size": len(html.encode("utf-8")),
            "text_size": len(text.encode("utf-8")),
        }
        delivery.error = ""
        delivery.save(update_fields=["status", "sent_at", "provider_response", "error"])
        return delivery

    api_key = str(getattr(settings, "RESEND_API_KEY", "") or "").strip()
    if not api_key:
        delivery.status = EmailDelivery.Status.FAILED
        delivery.failed_at = timezone.now()
        delivery.error = "RESEND_API_KEY manquante."
        delivery.save(update_fields=["status", "failed_at", "error"])
        return delivery

    payload = {
        "from": f"{config.resend_from_name} <{config.resend_from_email}>",
        "to": [delivery.recipient],
        "subject": delivery.subject,
        "html": html,
        "text": text,
        "tags": [{"name": "event", "value": delivery.event_type.replace("_", "-")[:256]}],
    }
    if config.resend_reply_to:
        payload["reply_to"] = config.resend_reply_to
    request = urllib.request.Request(
        f"{str(getattr(settings, 'RESEND_API_BASE', 'https://api.resend.com')).rstrip('/')}/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Idempotency-Key": f"kalanpro:{delivery.event_key}"[:256],
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=int(getattr(settings, "RESEND_HTTP_TIMEOUT", 15))) as response:
            response_payload = json.loads(response.read().decode("utf-8") or "{}")
        delivery.status = EmailDelivery.Status.SENT
        delivery.sent_at = timezone.now()
        delivery.provider_message_id = str(response_payload.get("id") or "")
        delivery.provider_response = response_payload
        delivery.error = ""
        delivery.save(update_fields=["status", "sent_at", "provider_message_id", "provider_response", "error"])
    except urllib.error.HTTPError as exc:
        try:
            parsed = json.loads(exc.read().decode("utf-8") or "{}")
        except Exception:
            parsed = {"detail": str(exc)}
        delivery.status = EmailDelivery.Status.FAILED
        delivery.failed_at = timezone.now()
        delivery.provider_response = parsed
        delivery.error = str(parsed)[:3000]
        delivery.save(update_fields=["status", "failed_at", "provider_response", "error"])
        logger.warning("Resend a refusé l'email %s: %s", delivery.id, delivery.error)
    except Exception as exc:
        delivery.status = EmailDelivery.Status.FAILED
        delivery.failed_at = timezone.now()
        delivery.error = str(exc)[:3000]
        delivery.save(update_fields=["status", "failed_at", "error"])
        logger.exception("Échec réseau Resend pour %s", delivery.id)
    return delivery


def queue_welcome_email(user):
    name = user.first_name or user.get_full_name() or user.username
    return queue_email_event(
        user=user,
        event_type=EmailDelivery.EventType.WELCOME,
        event_key=f"welcome:{user.id}",
        subject="Bienvenue sur KalanPro",
        context={
            "eyebrow": "Bienvenue",
            "title": "Votre parcours KalanPro commence maintenant",
            "greeting": f"Bonjour {name},",
            "intro": "Votre compte est prêt. Vous pouvez apprendre, rejoindre des cohortes, trouver un mentor et découvrir des opportunités professionnelles depuis un seul espace.",
            "details": [
                {"label": "Compte", "value": user.email},
                {"label": "Région", "value": user.country or "Afrique francophone"},
            ],
            "cta_label": "Découvrir KalanPro",
            "cta_url": settings.FRONTEND_URL.rstrip("/"),
            "footer_note": "Vous recevez cet email car un compte KalanPro vient d'être créé avec cette adresse.",
        },
        metadata={"user_id": user.id},
        force=True,
    )


def queue_password_reset_email(user, reset_url):
    name = user.first_name or user.get_full_name() or user.username
    return queue_email_event(
        user=user,
        event_type=EmailDelivery.EventType.PASSWORD_RESET,
        event_key=f"password-reset:{user.id}:{reset_url.rsplit('/', 1)[-1]}",
        subject="Réinitialisez votre mot de passe KalanPro",
        context={
            "eyebrow": "Sécurité du compte",
            "title": "Choisissez un nouveau mot de passe",
            "greeting": f"Bonjour {name},",
            "intro": "Nous avons reçu une demande de réinitialisation du mot de passe associé à votre compte KalanPro.",
            "body": "Si vous n'êtes pas à l'origine de cette demande, vous pouvez ignorer cet email. Votre mot de passe actuel reste inchangé.",
            "cta_label": "Réinitialiser mon mot de passe",
            "cta_url": reset_url,
            "footer_note": "Pour votre sécurité, ne transférez jamais ce lien à une autre personne.",
        },
        metadata={"user_id": user.id},
        force=True,
    )


def queue_session_invite_email(*, inviter, recipient, session, join_url, register_url):
    event_key = f"session-invite:{session.id}:{recipient.lower()}:{timezone.now().strftime('%Y%m%d%H%M%S%f')}"
    return queue_email_event(
        recipient=recipient,
        event_type=EmailDelivery.EventType.SESSION_INVITE,
        event_key=event_key,
        subject=f"Invitation KalanPro : {session.formation.title}",
        context={
            "eyebrow": "Invitation à une séance",
            "title": session.formation.title,
            "greeting": "Bonjour,",
            "intro": f"{inviter.get_full_name() or inviter.username} vous invite à participer à la séance {session.session_number} sur KalanPro.",
            "details": [
                {"label": "Séance", "value": f"Séance {session.session_number}"},
                {"label": "Date", "value": timezone.localtime(session.scheduled_at).strftime("%d/%m/%Y à %H:%M")},
                {"label": "Durée", "value": f"{session.duration_minutes} min"},
            ],
            "body": f"Si vous n'avez pas encore de compte, créez-le avec cette adresse : {register_url}",
            "cta_label": "Rejoindre la séance",
            "cta_url": join_url,
            "footer_note": "Cette invitation donne accès uniquement à cette séance et ne vous inscrit pas automatiquement à la formation.",
        },
        metadata={"session_id": session.id, "invited_by": inviter.id},
        force=True,
    )


def create_admin_email_test_delivery(*, user, recipient):
    import uuid
    return queue_email_event(
        user=user,
        recipient=recipient,
        event_type=EmailDelivery.EventType.TEST,
        event_key=f"email-test:{uuid.uuid4().hex}",
        subject="Test email KalanPro via Resend",
        context={
            "eyebrow": "Diagnostic email",
            "title": "Votre configuration Resend fonctionne",
            "greeting": f"Bonjour {user.first_name or user.get_full_name() or user.username},",
            "intro": "Cet email confirme que KalanPro peut générer et mettre en file un email transactionnel au format HTML professionnel.",
            "details": [{"label": "Canal", "value": "Resend Email API"}, {"label": "Environnement", "value": "KalanPro"}],
            "cta_label": "Ouvrir KalanPro",
            "cta_url": settings.FRONTEND_URL.rstrip("/"),
            "footer_note": "Message de diagnostic demandé depuis l'administration KalanPro.",
        },
        metadata={"requested_by_admin": user.id},
        force=True,
    )
