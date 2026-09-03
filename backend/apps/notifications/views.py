import hashlib
import hmac
import json

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.throttles import AdminTestRateThrottle, WebhookRateThrottle
from .models import NotificationPreference, WhatsAppDelivery
from .serializers import NotificationPreferenceSerializer, WhatsAppDeliverySerializer
from .services import create_admin_test_delivery, whatsapp_runtime_status


class IsAdminRole(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "admin")


class NotificationPreferenceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _obj(self, user):
        obj, _ = NotificationPreference.objects.get_or_create(user=user)
        return obj

    def get(self, request):
        return Response(NotificationPreferenceSerializer(self._obj(request.user)).data)

    def patch(self, request):
        obj = self._obj(request.user)
        serializer = NotificationPreferenceSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AdminWhatsAppStatusView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        runtime = whatsapp_runtime_status()
        runtime.update({
            "webhook_url": f"{settings.BACKEND_PUBLIC_URL.rstrip('/')}/api/notifications/whatsapp/webhook/",
            "opted_in_users": NotificationPreference.objects.filter(whatsapp_opt_in=True).count(),
            "queued": WhatsAppDelivery.objects.filter(status=WhatsAppDelivery.Status.QUEUED).count(),
            "failed": WhatsAppDelivery.objects.filter(status=WhatsAppDelivery.Status.FAILED).count(),
            "sent_or_better": WhatsAppDelivery.objects.filter(
                status__in=[WhatsAppDelivery.Status.SENT, WhatsAppDelivery.Status.DELIVERED, WhatsAppDelivery.Status.READ]
            ).count(),
        })
        return Response(runtime)


class AdminWhatsAppTestView(APIView):
    permission_classes = [IsAdminRole]
    throttle_classes = [AdminTestRateThrottle]

    def post(self, request):
        phone = str(request.data.get("phone") or "").strip()
        if not phone:
            return Response({"phone": ["Numéro requis au format international."]}, status=400)
        try:
            delivery = create_admin_test_delivery(user=request.user, phone=phone)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(WhatsAppDeliverySerializer(delivery).data, status=status.HTTP_202_ACCEPTED)


class WhatsAppWebhookView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [WebhookRateThrottle]

    def get(self, request):
        mode = request.query_params.get("hub.mode")
        token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge", "")
        expected = str(getattr(settings, "WHATSAPP_VERIFY_TOKEN", "") or "")
        if mode == "subscribe" and expected and hmac.compare_digest(str(token or ""), expected):
            return HttpResponse(challenge, content_type="text/plain", status=200)
        return Response({"detail": "Vérification WhatsApp refusée."}, status=403)

    def _valid_signature(self, request):
        app_secret = str(getattr(settings, "WHATSAPP_APP_SECRET", "") or "")
        if not app_secret:
            return bool(settings.DEBUG or getattr(settings, "WHATSAPP_DRY_RUN", True))
        received = str(request.META.get("HTTP_X_HUB_SIGNATURE_256", "") or "")
        if not received.startswith("sha256="):
            return False
        expected = "sha256=" + hmac.new(app_secret.encode("utf-8"), request.body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(received, expected)

    def post(self, request):
        if not self._valid_signature(request):
            return Response({"detail": "Signature webhook WhatsApp invalide."}, status=403)
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except Exception:
            return Response({"detail": "JSON invalide."}, status=400)
        updated = 0
        for entry in payload.get("entry", []) or []:
            for change in entry.get("changes", []) or []:
                value = change.get("value") or {}
                for item in value.get("statuses", []) or []:
                    provider_id = str(item.get("id") or "")
                    provider_status = str(item.get("status") or "").lower()
                    if not provider_id:
                        continue
                    delivery = WhatsAppDelivery.objects.filter(provider_message_id=provider_id).first()
                    if not delivery:
                        continue
                    now = timezone.now()
                    fields = ["provider_response"]
                    delivery.provider_response = item
                    if provider_status == "sent":
                        delivery.status = WhatsAppDelivery.Status.SENT
                        delivery.sent_at = delivery.sent_at or now
                        fields += ["status", "sent_at"]
                    elif provider_status == "delivered":
                        delivery.status = WhatsAppDelivery.Status.DELIVERED
                        delivery.delivered_at = now
                        fields += ["status", "delivered_at"]
                    elif provider_status == "read":
                        delivery.status = WhatsAppDelivery.Status.READ
                        delivery.read_at = now
                        fields += ["status", "read_at"]
                    elif provider_status == "failed":
                        delivery.status = WhatsAppDelivery.Status.FAILED
                        delivery.failed_at = now
                        errors = item.get("errors") or []
                        delivery.error = json.dumps(errors, ensure_ascii=False)[:3000]
                        fields += ["status", "failed_at", "error"]
                    delivery.save(update_fields=list(dict.fromkeys(fields)))
                    updated += 1
        return Response({"received": True, "updated": updated})
