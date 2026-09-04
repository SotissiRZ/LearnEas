from io import BytesIO
from pathlib import Path
import tempfile
from decimal import Decimal
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from pypdf import PdfWriter
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.enrollments.models import CourseEnrollment
from .models import Domain, Category, Course, Section, Lesson, PDFResource, PDFProduct


def pdf_bytes(page_count=3):
    output = BytesIO()
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=612, height=792)
    writer.write(output)
    return output.getvalue()


class CatalogAccessRegressionTests(APITestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username="trainer", email="trainer@example.com", password="passpass123", role=User.Role.INSTRUCTOR
        )
        self.student = User.objects.create_user(
            username="student", email="student2@example.com", password="passpass123", role=User.Role.STUDENT
        )
        self.admin = User.objects.create_user(
            username="adminrole", email="adminrole@example.com", password="passpass123", role=User.Role.ADMIN
        )
        self.category = Category.objects.create(name="Développement")
        self.course = Course.objects.create(
            instructor=self.instructor,
            category=self.category,
            title="Django complet",
            description="Cours de test",
            price=Decimal("200.00"),
            published=True,
        )
        self.section = Section.objects.create(course=self.course, title="Module 1", order=1)
        self.lesson = Lesson.objects.create(
            section=self.section,
            title="Introduction",
            video_url="https://cdn.example.com/video.mp4",
            duration_minutes=10,
            order=1,
            subtitles_file=SimpleUploadedFile(
                "intro.vtt", b"WEBVTT\n\n00:00.000 --> 00:02.000\nBonjour", content_type="text/vtt"
            ),
            transcript="Transcription complete reservee aux inscrits.",
        )
        self.pdf = PDFResource.objects.create(
            course=self.course,
            title="Support",
            file=SimpleUploadedFile("support.pdf", pdf_bytes(2), content_type="application/pdf"),
            page_count=2,
        )

    def test_owner_can_read_own_locked_course_media(self):
        self.client.force_authenticate(self.instructor)
        response = self.client.get(f"/api/catalog/courses/{self.course.slug}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_enrolled"])
        self.assertFalse(response.data["sections"][0]["lessons"][0]["locked"])
        self.assertIsNotNone(response.data["sections"][0]["lessons"][0]["video_url"])
        self.assertFalse(response.data["pdf_resources"][0]["locked"])
        self.assertIsNotNone(response.data["pdf_resources"][0]["file"])

    def test_paid_enrollment_unlocks_course_media(self):
        CourseEnrollment.objects.create(user=self.student, course=self.course)
        self.client.force_authenticate(self.student)
        response = self.client.get(f"/api/catalog/courses/{self.course.slug}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_enrolled"])
        self.assertFalse(response.data["sections"][0]["lessons"][0]["locked"])


    def test_locked_lesson_does_not_leak_subtitles_or_transcript(self):
        self.client.force_authenticate(self.student)
        response = self.client.get(f"/api/catalog/courses/{self.course.slug}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        lesson = response.data["sections"][0]["lessons"][0]
        self.assertTrue(lesson["locked"])
        self.assertIsNone(lesson["video_url"])
        self.assertIsNone(lesson["video_file"])
        self.assertIsNone(lesson["subtitles_file"])
        self.assertEqual(lesson["transcript"], "")

    def test_student_cannot_bypass_locks_through_management_endpoints(self):
        self.client.force_authenticate(self.student)
        response = self.client.get(f"/api/catalog/lessons/{self.lesson.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.get(f"/api/catalog/pdf-resources/{self.pdf.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_pdf_page_count_is_extracted_automatically(self):
        self.client.force_authenticate(self.instructor)
        upload = SimpleUploadedFile("auto.pdf", pdf_bytes(4), content_type="application/pdf")
        response = self.client.post(
            "/api/catalog/pdf-resources/",
            {"course": self.course.id, "title": "Auto pages", "file": upload, "order": 2},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["page_count"], 4)


    @override_settings(MAX_VIDEO_UPLOAD_MB=1)
    def test_video_upload_limit_is_configurable_and_reported_before_ffprobe(self):
        self.client.force_authenticate(self.instructor)
        oversized = SimpleUploadedFile(
            "oversized.mp4",
            b"0" * (1024 * 1024 + 1),
            content_type="video/mp4",
        )
        response = self.client.post(
            "/api/catalog/lessons/",
            {
                "section": self.section.id,
                "title": "Vidéo trop lourde",
                "video_file": oversized,
                "order": 2,
                "is_preview": False,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn("1 Mo", str(response.data))


    def test_video_upload_returns_without_sync_ffmpeg_or_ffprobe(self):
        self.client.force_authenticate(self.instructor)
        fake_video = SimpleUploadedFile("async.mp4", b"not-a-real-video", content_type="video/mp4")
        with patch("apps.catalog.tasks.normalize_lesson_video.delay"):
            response = self.client.post(
                "/api/catalog/lessons/",
                {
                    "section": self.section.id,
                    "title": "Traitement asynchrone",
                    "video_file": fake_video,
                    "order": 3,
                    "is_preview": False,
                },
                format="multipart",
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        created = Lesson.objects.get(title="Traitement asynchrone")
        self.assertEqual(created.duration_minutes, 0)
        self.assertEqual(created.streaming_status, "pending")

    @override_settings(USE_S3=False, DIRECT_MEDIA_UPLOADS_ENABLED=False)
    def test_upload_capabilities_keep_local_fallback(self):
        self.client.force_authenticate(self.instructor)
        response = self.client.get("/api/catalog/lessons/upload-capabilities/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["direct_multipart"])

    @override_settings(USE_S3=True, DIRECT_MEDIA_UPLOADS_ENABLED=True)
    @patch("apps.catalog.direct_uploads.initiate_multipart_upload")
    def test_owner_can_start_direct_multipart_upload(self, initiate):
        initiate.return_value = {
            "object_key": f"courses/videos/direct/{self.instructor.id}/abc.mp4",
            "upload_id": "upload-123",
            "part_size_bytes": 16 * 1024 * 1024,
            "parts_count": 2,
            "content_type": "video/mp4",
        }
        self.client.force_authenticate(self.instructor)
        response = self.client.post(
            "/api/catalog/lessons/direct-upload-start/",
            {"section": self.section.id, "filename": "cours.mp4", "size": 20 * 1024 * 1024},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["upload_id"], "upload-123")
        initiate.assert_called_once()

    @patch("apps.catalog.tasks.normalize_lesson_video.delay")
    @patch("apps.catalog.direct_uploads.complete_multipart_upload")
    def test_direct_multipart_completion_creates_pending_lesson(self, complete, normalize_delay):
        object_key = f"courses/videos/direct/{self.instructor.id}/abc.mp4"
        complete.return_value = {"object_key": object_key, "size": 1234}
        self.client.force_authenticate(self.instructor)
        response = self.client.post(
            "/api/catalog/lessons/direct-upload-complete/",
            {
                "section": self.section.id,
                "title": "Vidéo S3",
                "order": "2",
                "is_preview": "false",
                "object_key": object_key,
                "upload_id": "upload-123",
                "expected_size": "1234",
                "parts": '[{"PartNumber":1,"ETag":"\"etag\""}]',
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        lesson = Lesson.objects.get(title="Vidéo S3")
        self.assertEqual(lesson.video_file.name, object_key)
        self.assertEqual(lesson.duration_minutes, 0)
        self.assertEqual(lesson.streaming_status, "pending")
        complete.assert_called_once()

    def test_private_video_media_endpoint_exposes_streaming_headers(self):
        self.lesson.video_url = ""
        self.lesson.video_file = SimpleUploadedFile("intro.mp4", b"fake-mp4-bytes", content_type="video/mp4")
        self.lesson.save(update_fields=["video_url", "video_file"])
        self.client.force_authenticate(self.instructor)
        detail = self.client.get(f"/api/catalog/courses/{self.course.slug}/")
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        protected_url = detail.data["sections"][0]["lessons"][0]["video_file"]
        self.assertTrue(protected_url.startswith("/api/media/private/?token="))

        media = self.client.get(protected_url, HTTP_RANGE="bytes=0-1023")
        self.assertEqual(media.status_code, status.HTTP_200_OK)
        self.assertEqual(media["Content-Type"], "video/mp4")
        self.assertEqual(media["Accept-Ranges"], "bytes")
        self.assertEqual(media["X-Accel-Buffering"], "no")
        self.assertIn("/_protected_media/", media["X-Accel-Redirect"])
        self.assertIn("inline", media["Content-Disposition"])
        self.assertEqual(media["X-Download-Options"], "noopen")

    def test_locked_lesson_does_not_leak_hls_urls(self):
        self.lesson.hls_master_path = "courses/hls/1/pkg/master.m3u8"
        self.lesson.audio_hls_path = "courses/hls/1/pkg/audio/index.m3u8"
        self.lesson.streaming_status = "ready"
        self.lesson.streaming_variants = [{"height": 240}, {"height": 360}]
        self.lesson.save(update_fields=["hls_master_path", "audio_hls_path", "streaming_status", "streaming_variants"])
        self.client.force_authenticate(self.student)
        response = self.client.get(f"/api/catalog/courses/{self.course.slug}/")
        lesson = response.data["sections"][0]["lessons"][0]
        self.assertTrue(lesson["locked"])
        self.assertIsNone(lesson["hls_url"])
        self.assertIsNone(lesson["audio_hls_url"])

    def test_hls_manifests_rewrite_nested_assets_to_signed_urls(self):
        with tempfile.TemporaryDirectory() as tmpdir, self.settings(MEDIA_ROOT=tmpdir, USE_S3=False):
            prefix = Path(tmpdir) / "courses" / "hls" / str(self.lesson.id) / "pkg"
            (prefix / "v240").mkdir(parents=True)
            (prefix / "audio").mkdir(parents=True)
            (prefix / "master.m3u8").write_text(
                "#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=340000,RESOLUTION=426x240\nv240/index.m3u8\n",
                encoding="utf-8",
            )
            (prefix / "v240" / "index.m3u8").write_text(
                "#EXTM3U\n#EXTINF:6.0,\nseg_00000.ts\n#EXT-X-ENDLIST\n",
                encoding="utf-8",
            )
            (prefix / "v240" / "seg_00000.ts").write_bytes(b"segment")
            (prefix / "audio" / "index.m3u8").write_text(
                "#EXTM3U\n#EXTINF:6.0,\nseg_00000.aac\n#EXT-X-ENDLIST\n",
                encoding="utf-8",
            )
            (prefix / "audio" / "seg_00000.aac").write_bytes(b"audio")

            relative = f"courses/hls/{self.lesson.id}/pkg"
            self.lesson.hls_master_path = f"{relative}/master.m3u8"
            self.lesson.audio_hls_path = f"{relative}/audio/index.m3u8"
            self.lesson.streaming_status = "ready"
            self.lesson.streaming_variants = [{"height": 240, "width": 426, "bandwidth": 340000}]
            self.lesson.save(update_fields=["hls_master_path", "audio_hls_path", "streaming_status", "streaming_variants"])

            self.client.force_authenticate(self.instructor)
            detail = self.client.get(f"/api/catalog/courses/{self.course.slug}/")
            lesson = detail.data["sections"][0]["lessons"][0]
            self.assertTrue(lesson["hls_url"].startswith("/api/media/hls/?token="))
            self.assertTrue(lesson["audio_hls_url"].startswith("/api/media/hls/?token="))

            master = self.client.get(lesson["hls_url"])
            self.assertEqual(master.status_code, status.HTTP_200_OK)
            self.assertEqual(master["Content-Type"].split(";")[0], "application/vnd.apple.mpegurl")
            variant_url = next(line for line in master.content.decode().splitlines() if line.startswith("/api/media/hls/?token="))

            variant = self.client.get(variant_url)
            self.assertEqual(variant.status_code, status.HTTP_200_OK)
            segment_url = next(line for line in variant.content.decode().splitlines() if line.startswith("/api/media/hls/?token="))

            segment = self.client.get(segment_url)
            self.assertEqual(segment.status_code, status.HTTP_200_OK)
            self.assertEqual(segment["Content-Type"], "video/mp2t")
            self.assertIn("/_protected_media/", segment["X-Accel-Redirect"])

    def test_private_video_rejects_direct_document_navigation(self):
        self.lesson.video_url = ""
        self.lesson.video_file = SimpleUploadedFile("intro.mp4", b"fake-mp4-bytes", content_type="video/mp4")
        self.lesson.save(update_fields=["video_url", "video_file"])
        self.client.force_authenticate(self.instructor)
        detail = self.client.get(f"/api/catalog/courses/{self.course.slug}/")
        protected_url = detail.data["sections"][0]["lessons"][0]["video_file"]

        blocked = self.client.get(protected_url, HTTP_SEC_FETCH_DEST="document")
        self.assertEqual(blocked.status_code, status.HTTP_403_FORBIDDEN)

        playable = self.client.get(protected_url, HTTP_SEC_FETCH_DEST="video")
        self.assertEqual(playable.status_code, status.HTTP_200_OK)
        self.assertEqual(playable["Content-Type"], "video/mp4")

    def test_private_media_x_accel_redirect_encodes_unicode_filename(self):
        self.lesson.video_url = ""
        self.lesson.video_file = SimpleUploadedFile("vidéo été.mp4", b"fake-mp4-bytes", content_type="video/mp4")
        self.lesson.save(update_fields=["video_url", "video_file"])
        self.client.force_authenticate(self.instructor)
        detail = self.client.get(f"/api/catalog/courses/{self.course.slug}/")
        protected_url = detail.data["sections"][0]["lessons"][0]["video_file"]
        media = self.client.get(protected_url)
        self.assertEqual(media.status_code, status.HTTP_200_OK)
        redirect_uri = media["X-Accel-Redirect"]
        self.assertNotIn(" ", redirect_uri)
        self.assertIn("%", redirect_uri)

    def test_private_pdf_media_endpoint_can_be_embedded_by_learneas(self):
        self.client.force_authenticate(self.instructor)
        detail = self.client.get(f"/api/catalog/courses/{self.course.slug}/")
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        protected_url = detail.data["pdf_resources"][0]["file"]
        self.assertTrue(protected_url.startswith("/api/media/private/?token="))

        media = self.client.get(protected_url)
        self.assertEqual(media.status_code, status.HTTP_200_OK)
        self.assertIn("/_protected_media/", media["X-Accel-Redirect"])
        self.assertEqual(media["Content-Type"], "application/pdf")
        self.assertIn("inline", media["Content-Disposition"])
        self.assertIn("frame-ancestors", media["Content-Security-Policy"])
        self.assertNotEqual(media.get("X-Frame-Options"), "DENY")


    def test_admin_can_read_every_lesson_and_pdf_for_editorial_review(self):
        self.course.published = False
        self.course.save(update_fields=["published"])
        self.client.force_authenticate(self.admin)
        response = self.client.get(f"/api/catalog/courses/{self.course.slug}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(response.data["is_enrolled"])
        lesson = response.data["sections"][0]["lessons"][0]
        self.assertFalse(lesson["locked"])
        self.assertEqual(lesson["video_url"], "https://cdn.example.com/video.mp4")
        self.assertFalse(response.data["pdf_resources"][0]["locked"])
        self.assertIsNotNone(response.data["pdf_resources"][0]["file"])

    def test_category_write_uses_learneas_admin_role(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/catalog/categories/",
            {"name": "Data", "icon": "Database", "description": "Data"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_instructor_can_create_course_when_featured_false_is_sent(self):
        self.client.force_authenticate(self.instructor)
        response = self.client.post(
            "/api/catalog/courses/",
            {
                "category": self.category.id,
                "title": "Cours créé par instructeur",
                "subtitle": "Sous-titre",
                "description": "Description",
                "price": "100.00",
                "is_free": False,
                "published": False,
                "featured": False,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        created = Course.objects.get(pk=response.data["id"])
        self.assertEqual(created.instructor_id, self.instructor.id)
        self.assertFalse(created.featured)

    def test_instructor_cannot_feature_course_even_if_true_is_sent(self):
        self.client.force_authenticate(self.instructor)
        response = self.client.patch(
            f"/api/catalog/courses/{self.course.slug}/",
            {"featured": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.course.refresh_from_db()
        self.assertFalse(self.course.featured)


class InstructorContentCreationTests(APITestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username="content_trainer", email="content-trainer@example.com", password="passpass123", role=User.Role.INSTRUCTOR
        )
        self.category = Category.objects.create(name="Création")
        self.client.force_authenticate(self.instructor)

    def test_instructor_can_create_standalone_pdf_when_featured_is_sent(self):
        upload = SimpleUploadedFile("guide.pdf", pdf_bytes(2), content_type="application/pdf")
        response = self.client.post(
            "/api/catalog/pdfs/",
            {
                "category": self.category.id,
                "title": "Guide instructeur",
                "description": "Document créé par un instructeur",
                "level": "beginner",
                "language": "Français",
                "price": "25.00",
                "is_free": False,
                "published": False,
                "featured": False,
                "file": upload,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        product = PDFProduct.objects.get(pk=response.data["id"])
        self.assertEqual(product.instructor_id, self.instructor.id)
        self.assertFalse(product.featured)
        self.assertEqual(product.page_count, 2)

    def test_instructor_cannot_self_feature_standalone_pdf(self):
        upload = SimpleUploadedFile("guide2.pdf", pdf_bytes(1), content_type="application/pdf")
        response = self.client.post(
            "/api/catalog/pdfs/",
            {
                "category": self.category.id,
                "title": "Guide non vedette",
                "description": "Test featured",
                "level": "beginner",
                "language": "Français",
                "price": "0",
                "is_free": True,
                "published": False,
                "featured": True,
                "file": upload,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        product = PDFProduct.objects.get(pk=response.data["id"])
        self.assertFalse(product.featured)


class CatalogDomainFilterTests(APITestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username="domaintrainer", email="domaintrainer@example.com", password="passpass123", role=User.Role.INSTRUCTOR
        )
        self.tech = Domain.objects.create(name="Technologie & Numérique", slug="technologie-numerique", order=10)
        self.design = Domain.objects.create(name="Design & Création", slug="design-creation", order=20)
        self.web = Category.objects.create(name="Développement Web Domain", domain=self.tech)
        self.ui = Category.objects.create(name="Design UI Domain", domain=self.design)
        self.course_web = Course.objects.create(
            instructor=self.instructor, category=self.web, title="Cours Web Domain", description="Web", price=10, published=True
        )
        self.course_ui = Course.objects.create(
            instructor=self.instructor, category=self.ui, title="Cours UI Domain", description="UI", price=10, published=True
        )

    def test_domains_endpoint_exposes_published_course_count(self):
        response = self.client.get("/api/catalog/domains/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        rows = {row["slug"]: row for row in response.data}
        self.assertEqual(rows["technologie-numerique"]["courses_count"], 1)
        self.assertEqual(rows["design-creation"]["courses_count"], 1)

    def test_course_catalog_can_filter_by_domain_slug(self):
        response = self.client.get("/api/catalog/courses/?category__domain__slug=design-creation")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        results = response.data["results"]
        self.assertEqual([row["slug"] for row in results], [self.course_ui.slug])
        self.assertEqual(results[0]["category"]["domain"]["slug"], "design-creation")

    def test_category_endpoint_includes_domain(self):
        response = self.client.get("/api/catalog/categories/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        row = next(item for item in response.data if item["slug"] == self.web.slug)
        self.assertEqual(row["domain"]["slug"], "technologie-numerique")

    def test_course_list_query_count_does_not_grow_per_card(self):
        with CaptureQueriesContext(connection) as initial:
            first = self.client.get("/api/catalog/courses/")
        self.assertEqual(first.status_code, status.HTTP_200_OK)

        for index in range(8):
            Course.objects.create(
                instructor=self.instructor,
                category=self.web,
                title=f"Cours perf {index}",
                description="Performance",
                price=10,
                published=True,
            )

        with CaptureQueriesContext(connection) as expanded:
            second = self.client.get("/api/catalog/courses/")
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        # Le nombre de requêtes doit rester essentiellement constant : auparavant les compteurs
        # catégorie/instructeur et les prefetch de leçons ajoutaient des requêtes par carte.
        self.assertLessEqual(len(expanded), len(initial) + 1)
