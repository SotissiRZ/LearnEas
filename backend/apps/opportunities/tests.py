from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from .models import EmployerProfile, Opportunity, OpportunityApplication

User = get_user_model()


class OpportunitySecurityTests(APITestCase):
    def setUp(self):
        self.recruiter = User.objects.create_user(username="recruiter", email="recruiter@example.com", password="StrongPass123!", country="Sénégal", role="employer")
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
        self.assertEqual(response.status_code, 403)

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


class EmployerRoleRegressionTests(APITestCase):
    def setUp(self):
        from apps.accounts.models import User
        from .models import EmployerProfile
        self.employer = User.objects.create_user(username="employer-role", email="employer-role@example.com", password="passpass123", role=User.Role.EMPLOYER)
        self.student = User.objects.create_user(username="student-role", email="student-role@example.com", password="passpass123", role=User.Role.STUDENT)
        self.profile = EmployerProfile.objects.create(user=self.employer, company_name="Entreprise test", country="Sénégal")

    def test_student_cannot_create_employer_profile(self):
        self.client.force_authenticate(self.student)
        response = self.client.post("/api/opportunities/employer-profile/", {"company_name": "Fausse entreprise", "country": "Sénégal"}, format="json")
        self.assertEqual(response.status_code, 403, response.data)

    def test_employer_cannot_apply_as_candidate(self):
        from .models import Opportunity
        self.profile.status = EmployerProfile.Status.APPROVED
        self.profile.save(update_fields=["status"])
        opportunity = Opportunity.objects.create(employer=self.profile, title="Test", description="Description", status=Opportunity.Status.PUBLISHED)
        self.client.force_authenticate(self.employer)
        response = self.client.post("/api/opportunities/applications/", {"opportunity": opportunity.id}, format="json")
        self.assertEqual(response.status_code, 403, response.data)


class RecruiterWorkspaceV75Tests(APITestCase):
    def setUp(self):
        from .models import CandidateProfile
        self.recruiter = User.objects.create_user(
            username="workspace-recruiter", email="workspace-recruiter@example.com",
            password="StrongPass123!", country="Côte d'Ivoire", role="employer",
        )
        self.student = User.objects.create_user(
            username="workspace-student", email="workspace-student@example.com",
            password="StrongPass123!", country="Sénégal", role="student",
            first_name="Fatou", last_name="Test",
        )
        self.employer = EmployerProfile.objects.create(
            user=self.recruiter, company_name="Workspace Africa", country="Côte d'Ivoire",
            description="Entreprise de test", status=EmployerProfile.Status.APPROVED,
        )
        self.talent = CandidateProfile.objects.create(
            user=self.student, headline="Data analyst", skills=["SQL", "Power BI"],
            years_experience=3, is_searchable=True,
        )
        self.job = Opportunity.objects.create(
            employer=self.employer, title="Data Analyst", description="Analyse de données",
            skills_required=["SQL"], screening_questions=["Pourquoi ce poste ?"],
            remote_worldwide=True, status=Opportunity.Status.PUBLISHED,
        )

    def test_branding_update_does_not_remove_approval(self):
        self.client.force_authenticate(self.recruiter)
        response = self.client.patch(
            f"/api/opportunities/employer-profile/{self.employer.id}/",
            {
                "tagline": "Construisons le numérique africain",
                "brand_color": "#112233",
                "values": ["Impact", "Autonomie"],
                "benefits": ["Télétravail"],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.employer.refresh_from_db()
        self.assertEqual(self.employer.status, EmployerProfile.Status.APPROVED)
        self.assertEqual(self.employer.brand_color, "#112233")

    def test_public_company_page_data_is_exposed_only_for_approved_company(self):
        self.employer.tagline = "Entreprise test"
        self.employer.values = ["Transparence"]
        self.employer.save(update_fields=["tagline", "values", "updated_at"])
        response = self.client.get(f"/api/opportunities/companies/{self.employer.slug}/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["company_name"], "Workspace Africa")
        self.assertEqual(response.data["values"], ["Transparence"])
        self.assertGreaterEqual(response.data["open_opportunities_count"], 1)

    def test_recruiter_can_bookmark_visible_talent(self):
        self.client.force_authenticate(self.recruiter)
        created = self.client.post(
            "/api/opportunities/talent-bookmarks/",
            {"talent": self.talent.id, "tags": ["prioritaire"]},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        listed = self.client.get("/api/opportunities/talent-bookmarks/")
        self.assertEqual(listed.status_code, 200, listed.data)
        rows = listed.data.get("results", listed.data) if isinstance(listed.data, dict) else listed.data
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["talent_detail"]["headline"], "Data analyst")

    def test_application_pipeline_metadata_is_saved(self):
        application = OpportunityApplication.objects.create(
            opportunity=self.job, candidate=self.student,
            candidate_name_snapshot="Fatou Test", candidate_email_snapshot=self.student.email,
        )
        self.client.force_authenticate(self.recruiter)
        response = self.client.post(
            f"/api/opportunities/applications/{application.id}/review/",
            {
                "status": "shortlisted",
                "recruiter_note": "Très bon profil",
                "recruiter_rating": 5,
                "recruiter_tags": ["prioritaire", "data"],
                "next_step_at": "2026-10-10T10:00:00Z",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        application.refresh_from_db()
        self.assertEqual(application.recruiter_rating, 5)
        self.assertEqual(application.recruiter_tags, ["prioritaire", "data"])
        self.assertEqual(application.status, OpportunityApplication.Status.SHORTLISTED)

    def test_candidate_can_answer_screening_questions(self):
        self.client.force_authenticate(self.student)
        response = self.client.post(
            "/api/opportunities/applications/",
            {
                "opportunity": self.job.id,
                "screening_answers": [{"question": "Pourquoi ce poste ?", "answer": "Pour mon expérience data."}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        application = OpportunityApplication.objects.get(pk=response.data["id"])
        self.assertEqual(application.screening_answers[0]["question"], "Pourquoi ce poste ?")

class RecruiterWorkspaceV76RegressionTests(APITestCase):
    def setUp(self):
        from .models import CandidateProfile
        self.recruiter = User.objects.create_user(
            username="v76-recruiter", email="v76-recruiter@example.com",
            password="StrongPass123!", country="Sénégal", role="employer",
        )
        self.employer = EmployerProfile.objects.create(
            user=self.recruiter, company_name="V76 Company", country="Sénégal",
            status=EmployerProfile.Status.APPROVED,
        )
        self.job = Opportunity.objects.create(
            employer=self.employer, title="Backend Engineer", description="Test",
            remote_worldwide=True, status=Opportunity.Status.PUBLISHED,
        )

    def test_recruiter_listing_serializes_company_without_field_error(self):
        self.client.force_authenticate(self.recruiter)
        response = self.client.get("/api/opportunities/listings/?mine=1&page_size=100")
        self.assertEqual(response.status_code, 200, response.data)
        rows = response.data.get("results", response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual(rows[0]["employer"]["company_name"], "V76 Company")

    def test_company_directory_counts_open_opportunities(self):
        response = self.client.get(f"/api/opportunities/companies/{self.employer.slug}/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["open_opportunities_count"], 1)
