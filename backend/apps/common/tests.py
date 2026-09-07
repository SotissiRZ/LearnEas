from unittest.mock import patch

from django.test import TestCase, override_settings


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
class HealthEndpointTests(TestCase):
    def test_liveness_does_not_require_dependencies(self):
        response = self.client.get("/api/health/live/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertTrue(response.headers.get("X-Request-ID"))

    def test_readiness_checks_database_and_cache(self):
        response = self.client.get("/api/health/ready/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["checks"], {"database": "ok", "cache": "ok"})

    @patch("learneas.urls.cache.get", side_effect=RuntimeError("cache unavailable"))
    def test_readiness_returns_503_when_dependency_is_down(self, _cache_get):
        response = self.client.get("/api/health/ready/")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["status"], "error")


class ClientTelemetryTests(TestCase):
    def test_client_error_telemetry_accepts_minimal_payload(self):
        response = self.client.post(
            "/api/telemetry/client-error/",
            {"name": "TypeError", "digest": "abc123", "pathname": "/courses"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 204)


class ImageUploadLimitTests(TestCase):
    @patch("apps.common.media_metadata.Image.open")
    def test_rejects_excessive_pixel_count(self, image_open):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from rest_framework import serializers
        from apps.common.media_metadata import validate_upload_limits

        fake_image = image_open.return_value.__enter__.return_value
        fake_image.size = (20000, 20000)
        upload = SimpleUploadedFile("huge.png", b"\x89PNG\r\n\x1a\nbody", content_type="image/png")
        with self.assertRaises(serializers.ValidationError):
            validate_upload_limits(
                upload, max_bytes=1024 * 1024, extensions={".png"}, field="image"
            )


from rest_framework.test import APITestCase
from apps.accounts.models import User


class AdminOperationsEndpointTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="ops_admin", email="ops-admin@example.com", password="StrongPass123!", role="admin"
        )
        self.student = User.objects.create_user(
            username="ops_student", email="ops-student@example.com", password="StrongPass123!", role="student"
        )

    @patch("apps.common.views.build_operations_snapshot")
    def test_admin_can_read_operations_snapshot(self, snapshot):
        snapshot.return_value = {"status": "ok", "services": {}, "metrics": {}, "providers": {}}
        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/ops/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "ok")

    @patch("apps.common.views.build_operations_snapshot")
    def test_non_admin_cannot_read_operations_snapshot(self, snapshot):
        snapshot.return_value = {"status": "ok"}
        self.client.force_authenticate(self.student)
        response = self.client.get("/api/ops/health/")
        self.assertEqual(response.status_code, 403)
        snapshot.assert_not_called()


class ReleaseResilienceTests(TestCase):
    @patch("learneas.urls.connection.cursor", side_effect=RuntimeError("database down"))
    def test_liveness_survives_database_failure(self, _cursor):
        response = self.client.get("/api/health/live/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    @patch("learneas.urls.cache.set", side_effect=RuntimeError("redis down"))
    def test_liveness_survives_cache_failure(self, _cache_set):
        response = self.client.get("/api/health/live/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    @patch("learneas.urls.connection.cursor", side_effect=RuntimeError("database down"))
    def test_readiness_fails_closed_when_database_is_down(self, _cursor):
        response = self.client.get("/api/health/ready/")
        self.assertEqual(response.status_code, 503)
        payload = response.json()
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["checks"]["database"], "error")


class ReleaseGateSnapshotTests(TestCase):
    @patch("apps.common.release._pending_migrations", return_value=[])
    @patch("apps.common.release._django_checks", return_value=[])
    @patch("apps.common.release._cache_check", return_value={"status": "ok"})
    @patch("apps.common.release._database_check", return_value={"status": "ok"})
    def test_release_gate_is_green_when_core_dependencies_are_green(
        self, _db, _cache, _checks, _migrations
    ):
        from apps.common.release import build_release_gate_snapshot

        snapshot = build_release_gate_snapshot()
        self.assertEqual(snapshot["status"], "ok")
        self.assertEqual(snapshot["blockers"], [])

    @patch("apps.common.release._pending_migrations", return_value=["catalog.9999_missing"])
    @patch("apps.common.release._django_checks", return_value=[])
    @patch("apps.common.release._cache_check", return_value={"status": "ok"})
    @patch("apps.common.release._database_check", return_value={"status": "ok"})
    def test_release_gate_blocks_pending_migrations(self, _db, _cache, _checks, _migrations):
        from apps.common.release import build_release_gate_snapshot

        snapshot = build_release_gate_snapshot()
        self.assertEqual(snapshot["status"], "error")
        self.assertIn("pending_migrations", snapshot["blockers"])

    @override_settings(REQUIRE_REMOTE_MEDIA=True)
    @patch("apps.common.release._storage_check", return_value={"status": "ok", "backend": "local"})
    @patch("apps.common.release._pending_migrations", return_value=[])
    @patch("apps.common.release._django_checks", return_value=[])
    @patch("apps.common.release._cache_check", return_value={"status": "ok"})
    @patch("apps.common.release._database_check", return_value={"status": "ok"})
    def test_release_gate_enforces_remote_media_contract(
        self, _db, _cache, _checks, _migrations, _storage
    ):
        from apps.common.release import build_release_gate_snapshot

        snapshot = build_release_gate_snapshot()
        self.assertEqual(snapshot["status"], "error")
        self.assertIn("remote_media_required", snapshot["blockers"])
