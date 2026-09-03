from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import PlatformSettings
from .models import NotificationPreference, WhatsAppDelivery
from .serializers import normalize_whatsapp_phone
from .services import send_delivery

User = get_user_model()


class WhatsAppNotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="wa-student", email="wa@example.com", password="StrongPass123!")
        self.pref = NotificationPreference.objects.create(user=self.user, whatsapp_phone="+221771234567", whatsapp_opt_in=True)
        cfg = PlatformSettings.load()
        cfg.whatsapp_enabled = True
        cfg.save(update_fields=["whatsapp_enabled"])

    def test_phone_normalization(self):
        self.assertEqual(normalize_whatsapp_phone("00 221 77 123 45 67"), "+221771234567")

    @override_settings(WHATSAPP_ENABLED=True, WHATSAPP_DRY_RUN=True)
    def test_dry_run_never_calls_meta(self):
        delivery = WhatsAppDelivery.objects.create(
            user=self.user, recipient=self.pref.whatsapp_phone, event_type="test", event_key="test:dry",
            template_name="hello_world", language_code="en_US",
        )
        send_delivery(delivery.id)
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, WhatsAppDelivery.Status.SIMULATED)

    def test_preferences_require_phone_for_opt_in(self):
        other = User.objects.create_user(username="other", email="other@example.com", password="StrongPass123!")
        client = APIClient()
        client.force_authenticate(other)
        response = client.patch("/api/notifications/preferences/", {"whatsapp_opt_in": True}, format="json")
        self.assertEqual(response.status_code, 400)
