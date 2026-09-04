from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from apps.catalog.models import Category, Course
from apps.enrollments.models import CourseEnrollment
from .models import ProjectAssignment, ProjectSubmission, PortfolioProfile

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
