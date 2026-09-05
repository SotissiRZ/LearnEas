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
