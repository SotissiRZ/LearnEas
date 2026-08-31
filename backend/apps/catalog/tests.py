from io import BytesIO
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from pypdf import PdfWriter
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.enrollments.models import CourseEnrollment
from .models import Category, Course, Section, Lesson, PDFResource, PDFProduct


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
