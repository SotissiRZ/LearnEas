from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from apps.catalog.models import Category, Course
from apps.enrollments.models import CourseEnrollment
from apps.enrollments.certificates import issue_course_certificate
from .models import ProjectAssignment, ProjectSubmission, PortfolioProfile, PortfolioItem

User = get_user_model()


class ProjectFlowTests(APITestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(username="mentor", email="mentor@example.com", password="x", role="instructor")
        self.student = User.objects.create_user(username="student", email="student@example.com", password="x", role="student")
        category = Category.objects.create(name="Data")
        self.course = Course.objects.create(
            instructor=self.instructor, category=category, title="Excel Pro", description="Cours", published=True,
            certificate_threshold_percent=100,
        )
        self.enrollment = CourseEnrollment.objects.create(user=self.student, course=self.course, progress_percent=100)
        self.assignment = ProjectAssignment.objects.create(
            course=self.course, title="Dashboard PME", brief="Construire un tableau de bord", required_for_certificate=True,
            max_score=100, passing_score=60,
        )

    def test_student_submit_instructor_approve_and_publish_portfolio(self):
        self.client.force_authenticate(self.student)
        response = self.client.post("/api/projects/submissions/", {
            "assignment": self.assignment.id,
            "title": "Mon dashboard",
            "summary": "Analyse de ventes",
            "external_url": "https://example.com/project",
            "skills": ["Excel", "Analyse"],
        }, format="json")
        self.assertEqual(response.status_code, 201)
        submission_id = response.data["id"]
        response = self.client.post(f"/api/projects/submissions/{submission_id}/submit/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "submitted")

        self.client.force_authenticate(self.instructor)
        response = self.client.post(f"/api/projects/submissions/{submission_id}/review/", {
            "status": "approved", "score": "85", "feedback": "Très bon travail"
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.enrollment.refresh_from_db()
        self.assertTrue(self.enrollment.completed)

        self.client.force_authenticate(self.student)
        response = self.client.post(f"/api/projects/submissions/{submission_id}/publish-portfolio/", {}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["is_verified"])
        profile = PortfolioProfile.objects.get(user=self.student)
        profile.is_public = True
        profile.save(update_fields=["is_public"])

        self.client.force_authenticate(None)
        response = self.client.get(f"/api/projects/portfolio/{profile.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["items"]), 1)
        self.assertTrue(response.data["items"][0]["is_verified"])

    def test_other_instructor_cannot_review(self):
        other = User.objects.create_user(username="other", email="other@example.com", password="x", role="instructor")
        submission = ProjectSubmission.objects.create(
            assignment=self.assignment, enrollment=self.enrollment, student=self.student, status="submitted", summary="x"
        )
        self.client.force_authenticate(other)
        response = self.client.post(f"/api/projects/submissions/{submission.id}/review/", {
            "status": "approved", "score": 90
        }, format="json")
        self.assertIn(response.status_code, (403, 404))


    def test_project_artifact_rejects_fake_zip_content(self):
        self.client.force_authenticate(self.student)
        fake = SimpleUploadedFile("sources.zip", b"not-a-zip", content_type="application/zip")
        response = self.client.post(
            "/api/projects/submissions/",
            {
                "assignment": self.assignment.id,
                "title": "Archive",
                "summary": "Sources",
                "artifact_file": fake,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("artifact_file", response.data)

    def test_private_portfolio_is_not_public(self):
        profile = PortfolioProfile.objects.create(user=self.student, slug="student-work", is_public=False)
        self.client.force_authenticate(None)
        response = self.client.get(f"/api/projects/portfolio/{profile.slug}/")
        self.assertEqual(response.status_code, 404)

    def test_rich_portfolio_fields_and_selected_certificate_are_public(self):
        self.client.force_authenticate(self.student)
        item = self.client.post(
            "/api/projects/portfolio-items/",
            {
                "title": "Plateforme data",
                "description": "Projet complet",
                "role": "Data analyst",
                "problem": "Données dispersées",
                "objective": "Centraliser les KPI",
                "outcome": "Reporting hebdomadaire automatisé",
                "stack": ["Excel", "Power BI"],
                "video_url": "https://example.com/demo",
                "skills": ["Analyse"],
                "is_public": True,
            },
            format="json",
        )
        self.assertEqual(item.status_code, 201, item.data)
        self.assertEqual(item.data["role"], "Data analyst")
        self.assertEqual(item.data["stack"], ["Excel", "Power BI"])

        certificate, _ = issue_course_certificate(self.enrollment, issued_by=self.instructor, force=True)
        profile = PortfolioProfile.objects.get(user=self.student)
        updated = self.client.patch(
            "/api/projects/portfolio-profile/me/",
            {
                "is_public": True,
                "show_certificates": True,
                "selected_certificate_ids": [certificate.id],
                "public_contact_email": "portfolio@example.com",
                "show_contact_email": True,
            },
            format="json",
        )
        self.assertEqual(updated.status_code, 200, updated.data)
        self.client.force_authenticate(None)
        public = self.client.get(f"/api/projects/portfolio/{profile.slug}/")
        self.assertEqual(public.status_code, 200, public.data)
        self.assertEqual(public.data["contact_email"], "portfolio@example.com")
        self.assertEqual(public.data["items"][0]["outcome"], "Reporting hebdomadaire automatisé")
        self.assertEqual(public.data["certificates"][0]["certificate_number"], certificate.certificate_number)

    def test_portfolio_cannot_select_another_users_certificate(self):
        self.enrollment.progress_percent = 100
        self.enrollment.save(update_fields=["progress_percent"])
        other = User.objects.create_user(username="student2", email="student2@example.com", password="x", role="student")
        other_enrollment = CourseEnrollment.objects.create(user=other, course=self.course, progress_percent=100)
        foreign_certificate, _ = issue_course_certificate(other_enrollment, issued_by=self.instructor, force=True)
        self.client.force_authenticate(self.student)
        response = self.client.patch(
            "/api/projects/portfolio-profile/me/",
            {"selected_certificate_ids": [foreign_certificate.id]},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("selected_certificate_ids", response.data)

