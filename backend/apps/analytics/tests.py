from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import ProductEvent

User = get_user_model()


class AnalyticsSecurityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(username="analytics-admin", email="analytics-admin@example.com", password="pass12345", role="admin", is_staff=True)
        self.student = User.objects.create_user(username="analytics-student", email="analytics-student@example.com", password="pass12345", role="student")

    def test_event_ingestion_discards_query_string_and_unknown_properties(self):
        response = self.client.post("/api/analytics/events/", {
            "event_name": "page_view",
            "session_id": "browser-session",
            "path": "/courses/python?token=secret",
            "properties": {"source": "navbar", "email": "private@example.com", "query": "secret search"},
        }, format="json")
        self.assertEqual(response.status_code, 204)
        event = ProductEvent.objects.get()
        self.assertEqual(event.path, "/courses/python")
        self.assertEqual(event.properties, {"source": "navbar"})
        self.assertEqual(len(event.session_key), 64)

    def test_admin_dashboard_is_admin_only(self):
        self.client.force_authenticate(self.student)
        self.assertEqual(self.client.get("/api/analytics/admin/overview/").status_code, 403)
        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/analytics/admin/overview/?period=30")
        self.assertEqual(response.status_code, 200)
        self.assertIn("finance", response.data)
        self.assertIn("timeline", response.data)

    def test_unknown_event_is_rejected(self):
        response = self.client.post("/api/analytics/events/", {"event_name": "password_captured"}, format="json")
        self.assertEqual(response.status_code, 400)
