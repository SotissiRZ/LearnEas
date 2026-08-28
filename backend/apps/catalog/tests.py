from io import BytesIO
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from pypdf import PdfWriter
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.enrollments.models import CourseEnrollment
from .models import Category, Course, Section, Lesson, PDFResource


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

    def test_category_write_uses_learneas_admin_role(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/catalog/categories/",
            {"name": "Data", "icon": "Database", "description": "Data"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
