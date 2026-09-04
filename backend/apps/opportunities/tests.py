from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from .models import EmployerProfile, Opportunity, OpportunityApplication

User = get_user_model()


class OpportunitySecurityTests(APITestCase):
    def setUp(self):
        self.recruiter = User.objects.create_user(username="recruiter", email="recruiter@example.com", password="StrongPass123!", country="Sénégal")
        self.student = User.objects.create_user(username="student", email="student@example.com", password="StrongPass123!", country="Sénégal")
        self.employer = EmployerProfile.objects.create(user=self.recruiter, company_name="Demo SARL", country="Sénégal", status=EmployerProfile.Status.APPROVED)
        self.job = Opportunity.objects.create(employer=self.employer, title="Analyste Excel", description="Test", country="Sénégal", skills_required=["Excel"], status=Opportunity.Status.PUBLISHED)

    def test_public_listing_is_visible(self):
        response = self.client.get("/api/opportunities/listings/")
        self.assertEqual(response.status_code, 200)

    def test_candidate_can_apply_once(self):
        self.client.force_authenticate(self.student)
        response = self.client.post("/api/opportunities/applications/", {"opportunity": self.job.id, "cover_letter": "Bonjour"}, format="json")
        self.assertEqual(response.status_code, 201)
        again = self.client.post("/api/opportunities/applications/", {"opportunity": self.job.id}, format="json")
        self.assertEqual(again.status_code, 409)

    def test_other_user_cannot_review_application(self):
        app = OpportunityApplication.objects.create(
            opportunity=self.job, candidate=self.student, candidate_name_snapshot="Student", candidate_email_snapshot=self.student.email
        )
        stranger = User.objects.create_user(username="x", email="x@example.com", password="StrongPass123!", country="Sénégal")
        self.client.force_authenticate(stranger)
        response = self.client.post(f"/api/opportunities/applications/{app.id}/review/", {"status": "shortlisted"}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_recruiter_cannot_apply_to_own_listing(self):
        self.client.force_authenticate(self.recruiter)
        response = self.client.post("/api/opportunities/applications/", {"opportunity": self.job.id}, format="json")
        self.assertEqual(response.status_code, 409)

    def test_talent_pool_requires_opt_in_and_approved_recruiter(self):
        from .models import CandidateProfile

        CandidateProfile.objects.create(user=self.student, headline="Analyste", skills=["Excel"], is_searchable=False)
        self.client.force_authenticate(self.recruiter)
        response = self.client.get("/api/opportunities/talents/")
        self.assertEqual(response.status_code, 200)
        rows = response.data.get("results", response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual(len(rows), 0)

        profile = self.student.candidate_profile
        profile.is_searchable = True
        profile.save(update_fields=["is_searchable", "updated_at"])
        response = self.client.get("/api/opportunities/talents/")
        rows = response.data.get("results", response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual(len(rows), 1)
        self.assertNotIn("email", rows[0])

    def test_withdrawn_application_cannot_be_reactivated_by_recruiter(self):
        app = OpportunityApplication.objects.create(
            opportunity=self.job,
            candidate=self.student,
            candidate_name_snapshot="Student",
            candidate_email_snapshot=self.student.email,
            status=OpportunityApplication.Status.WITHDRAWN,
        )
        self.client.force_authenticate(self.recruiter)
        response = self.client.post(f"/api/opportunities/applications/{app.id}/review/", {"status": "shortlisted"}, format="json")
        self.assertEqual(response.status_code, 409)


    def test_approved_employer_identity_change_requires_reapproval(self):
        self.client.force_authenticate(self.recruiter)
        response = self.client.patch(
            f"/api/opportunities/employer-profile/{self.employer.id}/",
            {"company_name": "Nouvelle identité SARL"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.employer.refresh_from_db()
        self.assertEqual(self.employer.status, EmployerProfile.Status.PENDING)

        self.client.force_authenticate(user=None)
        listing = self.client.get("/api/opportunities/listings/")
        rows = listing.data.get("results", listing.data) if isinstance(listing.data, dict) else listing.data
        self.assertFalse(any(row["id"] == self.job.id for row in rows))

    def test_candidate_resume_rejects_fake_pdf_content(self):
        self.client.force_authenticate(self.student)
        fake = SimpleUploadedFile("cv.pdf", b"MZ-not-a-pdf", content_type="application/pdf")
        response = self.client.patch(
            "/api/opportunities/candidate-profile/me/",
            {"resume": fake},
            format="multipart",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("resume", response.data)

    def test_hidden_salary_is_not_exposed_publicly(self):
        self.job.salary_min = 100000
        self.job.salary_max = 200000
        self.job.salary_currency = "XOF"
        self.job.show_salary = False
        self.job.save()
        self.client.force_authenticate(user=None)
        response = self.client.get(f"/api/opportunities/listings/{self.job.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["salary_min"])
        self.assertIsNone(response.data["salary_max"])
