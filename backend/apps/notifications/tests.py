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
        with self.assertRaises(Exception):
            normalize_whatsapp_phone("+99912345678")

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

class ResendEmailNotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="email-student", email="email@example.com", password="StrongPass123!", first_name="Awa")
        NotificationPreference.objects.create(user=self.user, email_enabled=True)
        cfg = PlatformSettings.load()
        cfg.resend_enabled = True
        cfg.resend_from_name = "KalanPro"
        cfg.resend_from_email = "notifications@kalanpro.com"
        cfg.save(update_fields=["resend_enabled", "resend_from_name", "resend_from_email"])

    @override_settings(RESEND_ENABLED=True, RESEND_DRY_RUN=True)
    def test_resend_dry_run_and_professional_template(self):
        from .email_services import queue_email_event, send_email, render_email
        from .models import EmailDelivery
        delivery = queue_email_event(
            user=self.user,
            event_type=EmailDelivery.EventType.TEST,
            event_key="email:test:dry-run",
            subject="Test KalanPro",
            context={
                "eyebrow": "Test",
                "title": "Notification professionnelle",
                "greeting": "Bonjour Awa,",
                "intro": "Ceci est un test.",
                "cta_label": "Ouvrir KalanPro",
                "cta_url": "https://kalanpro.com",
            },
            force=True,
        )
        self.assertIsNotNone(delivery)
        html, text = render_email(delivery)
        self.assertIn("Kalan", html)
        self.assertIn("#ff641a", html)
        self.assertIn("Ouvrir KalanPro", html)
        self.assertIn("https://kalanpro.com", text)
        send_email(delivery.id)
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, EmailDelivery.Status.SIMULATED)

    @override_settings(RESEND_ENABLED=True, RESEND_DRY_RUN=True)
    def test_user_can_disable_email_channel(self):
        from .email_services import queue_email_event
        from .models import EmailDelivery
        pref = self.user.notification_preferences
        pref.email_enabled = False
        pref.save(update_fields=["email_enabled"])
        delivery = queue_email_event(
            user=self.user,
            event_type=EmailDelivery.EventType.PAYMENT,
            event_key="email:test:disabled",
            subject="Paiement",
            context={"title": "Paiement"},
        )
        self.assertIsNone(delivery)
