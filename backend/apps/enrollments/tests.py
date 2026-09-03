from decimal import Decimal
from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, PlatformSettings
from apps.catalog.models import Category, Course
from apps.formations.models import InteractiveFormation, FormationEnrollment, FormationSession, FormationAttendance
from .models import CourseEnrollment, Certificate
from .certificates import course_eligibility, formation_eligibility, issue_course_certificate, issue_formation_certificate


class CertificateRegressionTests(APITestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username="cert_trainer", email="cert-trainer@example.com", password="passpass123", role=User.Role.INSTRUCTOR
        )
        self.student = User.objects.create_user(
            username="cert_student", email="cert-student@example.com", password="passpass123", role=User.Role.STUDENT,
            first_name="Fatou", last_name="Test",
        )
        self.other_student = User.objects.create_user(
            username="cert_other", email="cert-other@example.com", password="passpass123", role=User.Role.STUDENT
        )
        self.admin = User.objects.create_user(
            username="cert_admin", email="cert-admin@example.com", password="passpass123", role=User.Role.ADMIN
        )
        self.category = Category.objects.create(name="Certification")
        self.course = Course.objects.create(
            instructor=self.instructor, category=self.category, title="Cours certifiant", description="Test",
            price=Decimal("99.00"), published=True, certificate_enabled=True,
            certificate_threshold_percent=80, certificate_auto_issue=True,
        )
        self.enrollment = CourseEnrollment.objects.create(user=self.student, course=self.course, progress_percent=79)

    def test_course_threshold_controls_eligibility_and_issue(self):
        self.assertFalse(course_eligibility(self.enrollment)["eligible"])
        self.enrollment.progress_percent = 80
        self.enrollment.save(update_fields=["progress_percent"])
        self.assertTrue(course_eligibility(self.enrollment)["eligible"])
        certificate, created = issue_course_certificate(self.enrollment, issued_by=self.instructor)
        self.assertTrue(created)
        self.assertEqual(certificate.student_name, "Fatou Test")
        self.assertEqual(certificate.achievement_percent, Decimal("80"))
        self.assertTrue(certificate.verification_code)

    def test_public_verification_exposes_no_student_email(self):
        self.enrollment.progress_percent = 100
        self.enrollment.save(update_fields=["progress_percent"])
        certificate, _ = issue_course_certificate(self.enrollment, issued_by=self.instructor)
        response = self.client.get(f"/api/enrollments/certificates/verify/{certificate.verification_code}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["student_name"], "Fatou Test")
        self.assertNotIn("email", response.data)
        self.assertNotIn("user", response.data)

    def test_public_verification_can_be_disabled_by_admin_setting(self):
        self.enrollment.progress_percent = 100
        self.enrollment.save(update_fields=["progress_percent"])
        certificate, _ = issue_course_certificate(self.enrollment, issued_by=self.instructor)
        settings = PlatformSettings.load()
        settings.certificate_verification_enabled = False
        settings.save()
        response = self.client.get(f"/api/enrollments/certificates/verify/{certificate.verification_code}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_student_cannot_read_another_students_certificate(self):
        self.enrollment.progress_percent = 100
        self.enrollment.save(update_fields=["progress_percent"])
        certificate, _ = issue_course_certificate(self.enrollment, issued_by=self.instructor)
        self.client.force_authenticate(self.other_student)
        response = self.client.get(f"/api/enrollments/certificates/{certificate.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_live_certificate_uses_recorded_attendance(self):
        formation = InteractiveFormation.objects.create(
            instructor=self.instructor, category=self.category, title="Live certifiant", description="Test",
            price=0, num_sessions=1, session_duration_minutes=60, max_students=10,
            certificate_enabled=True, certificate_attendance_percent=80,
        )
        enrollment = FormationEnrollment.objects.create(user=self.student, formation=formation)
        session = FormationSession.objects.create(
            formation=formation, session_number=1, scheduled_at=timezone.now(), duration_minutes=60,
            started_at=timezone.now() - timedelta(hours=1), ended_at=timezone.now(), actual_duration_seconds=3600,
            completed=True,
        )
        FormationAttendance.objects.create(
            session=session, user=self.student, duration_seconds=3000,
            left_at=timezone.now(), last_seen_at=timezone.now(),
        )
        info = formation_eligibility(enrollment)
        self.assertTrue(info["eligible"])
        self.assertGreaterEqual(info["percent"], 80)
        certificate, created = issue_formation_certificate(enrollment, issued_by=self.instructor)
        self.assertTrue(created)
        self.assertEqual(certificate.content_type, "formation")

    def test_bulk_issue_only_issues_eligible_students(self):
        self.enrollment.progress_percent = 100
        self.enrollment.save(update_fields=["progress_percent"])
        CourseEnrollment.objects.create(user=self.other_student, course=self.course, progress_percent=10)
        self.client.force_authenticate(self.instructor)
        response = self.client.post(
            "/api/enrollments/certificates/issue-bulk/", {"course_id": self.course.id}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["issued_count"], 1)
        self.assertTrue(Certificate.objects.filter(user=self.student, course_enrollment=self.enrollment).exists())
        self.assertFalse(Certificate.objects.filter(user=self.other_student).exists())


class LearningPlayerRegressionTests(APITestCase):
    def setUp(self):
        from apps.catalog.models import Section, Lesson
        self.instructor = User.objects.create_user(
            username="player_trainer", email="player-trainer@example.com", password="passpass123", role=User.Role.INSTRUCTOR
        )
        self.student = User.objects.create_user(
            username="player_student", email="player-student@example.com", password="passpass123", role=User.Role.STUDENT
        )
        self.other = User.objects.create_user(
            username="player_other", email="player-other@example.com", password="passpass123", role=User.Role.STUDENT
        )
        self.category = Category.objects.create(name="Player")
        self.course = Course.objects.create(
            instructor=self.instructor, category=self.category, title="Cours lecteur", description="Test",
            price=Decimal("25.00"), published=True,
        )
        self.section = Section.objects.create(course=self.course, title="Chapitre 1", order=1)
        self.lesson = Lesson.objects.create(
            section=self.section, title="Leçon 1", duration_minutes=10, order=1,
            transcript="[00:00] Introduction\n[01:15] Démonstration",
        )
        self.enrollment = CourseEnrollment.objects.create(user=self.student, course=self.course)

    def test_private_timestamped_note_crud_is_scoped_to_owner(self):
        self.client.force_authenticate(self.student)
        created = self.client.post(
            "/api/enrollments/lesson-notes/",
            {"lesson": self.lesson.id, "timestamp_seconds": 75, "content": "Point important"},
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
        note_id = created.data["id"]

        listing = self.client.get(f"/api/enrollments/lesson-notes/?lesson={self.lesson.id}")
        self.assertEqual(listing.status_code, status.HTTP_200_OK, listing.data)
        self.assertEqual(len(listing.data), 1)
        self.assertEqual(listing.data[0]["timestamp_seconds"], 75)

        self.client.force_authenticate(self.other)
        hidden = self.client.get(f"/api/enrollments/lesson-notes/{note_id}/")
        self.assertEqual(hidden.status_code, status.HTTP_404_NOT_FOUND)

    def test_non_enrolled_student_cannot_create_note(self):
        self.client.force_authenticate(self.other)
        response = self.client.post(
            "/api/enrollments/lesson-notes/",
            {"lesson": self.lesson.id, "timestamp_seconds": 10, "content": "Interdit"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_player_progress_persists_resume_position(self):
        self.client.force_authenticate(self.student)
        response = self.client.post(
            f"/api/enrollments/my-courses/{self.enrollment.id}/update-lesson-progress/",
            {"lesson_id": self.lesson.id, "watched_seconds": 137},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["last_position_seconds"], 137)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.last_accessed_lesson_id, self.lesson.id)

        listing = self.client.get("/api/enrollments/my-courses/")
        self.assertEqual(listing.status_code, status.HTTP_200_OK, listing.data)
        row = listing.data["results"][0]
        self.assertEqual(row["last_accessed_lesson"], self.lesson.id)
        self.assertEqual(row["lesson_progress"][0]["last_position_seconds"], 137)
