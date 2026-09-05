from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile, TemporaryUploadedFile
from django.test import override_settings
from django.utils import timezone
from datetime import timedelta
import base64
import tempfile
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
        # Le queryset masque les candidatures d'autrui : 404 évite de révéler
        # l'existence d'une candidature à un utilisateur non autorisé.
        self.assertEqual(response.status_code, 404)

    def test_recruiter_cannot_apply_to_own_listing(self):
        self.client.force_authenticate(self.recruiter)
        response = self.client.post("/api/opportunities/applications/", {"opportunity": self.job.id}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_talent_pool_requires_opt_in_and_paid_approved_recruiter(self):
        from .models import CandidateProfile
        from apps.payments.models import Order
        from apps.opportunities.services import activate_employer_entitlement

        CandidateProfile.objects.create(user=self.student, headline="Analyste", skills=["Excel"], is_searchable=False)
        self.client.force_authenticate(self.recruiter)
        denied = self.client.get("/api/opportunities/talents/")
        self.assertEqual(denied.status_code, 403, denied.data)

        order = Order.objects.create(
            user=self.recruiter, status=Order.Status.PAID, provider=Order.Provider.MANUAL,
            provider_sandbox=True, base_total_amount="30.34", total_amount="30.34", currency="EUR",
            paid_at=timezone.now(),
        )
        activate_employer_entitlement(order, kind="pro")
        hidden = self.client.get("/api/opportunities/talents/")
        self.assertEqual(hidden.status_code, 200, hidden.data)
        rows = hidden.data.get("results", hidden.data) if isinstance(hidden.data, dict) else hidden.data
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

    def test_employer_logo_and_banner_accept_temporary_multipart_files(self):
        # Reproduit le chemin réel des gros uploads Django : TemporaryUploadedFile
        # repose sur un flux BufferedRandom qui ne peut pas être deep-copié/picklé.
        # PNG 2×2 réellement valide (le fixture précédent avait un checksum IDAT
        # corrompu et était donc correctement rejeté par ImageField/Pillow).
        png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAFklEQVR4nGP8z8DAwMDAxMDAwMDAAAANHQEDasKb6QAAAABJRU5ErkJggg=="
        )

        def uploaded(name):
            value = TemporaryUploadedFile(name, "image/png", len(png), None)
            value.write(png)
            value.seek(0)
            return value

        self.client.force_authenticate(self.recruiter)
        with tempfile.TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            response = self.client.patch(
                f"/api/opportunities/employer-profile/{self.employer.id}/",
                {
                    "tagline": "Entreprise panafricaine",
                    "values": '["Impact", "Confiance"]',
                    "benefits": '["Télétravail", "Formation"]',
                    "hiring_regions": '["Sénégal", "Côte d’Ivoire"]',
                    "logo": uploaded("logo.png"),
                    "banner": uploaded("banner.png"),
                },
                format="multipart",
            )
            self.assertEqual(response.status_code, 200, response.data)
            self.employer.refresh_from_db()
            self.assertTrue(bool(self.employer.logo))
            self.assertTrue(bool(self.employer.banner))
            self.assertEqual(self.employer.values, ["Impact", "Confiance"])
            self.assertEqual(self.employer.benefits, ["Télétravail", "Formation"])
            self.assertEqual(self.employer.hiring_regions, ["Sénégal", "Côte d’Ivoire"])
            self.assertEqual(self.employer.status, EmployerProfile.Status.APPROVED)

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

    def activate_pro(self):
        from apps.payments.models import Order
        from apps.opportunities.services import activate_employer_entitlement
        order = Order.objects.create(
            user=self.recruiter, status=Order.Status.PAID, provider=Order.Provider.MANUAL,
            provider_sandbox=True, base_total_amount="30.34", total_amount="30.34", currency="EUR",
            paid_at=timezone.now(),
        )
        return activate_employer_entitlement(order, kind="pro")

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
        self.activate_pro()
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


class RecruiterGovernanceV78Tests(APITestCase):
    def setUp(self):
        from apps.accounts.models import PlatformSettings
        from apps.payments.models import Currency, Order
        from .models import CandidateProfile

        self.recruiter = User.objects.create_user(
            username="v78-recruiter", email="v78-recruiter@example.com",
            password="StrongPass123!", country="Sénégal", role="employer",
        )
        self.student = User.objects.create_user(
            username="v78-student", email="v78-student@example.com",
            password="StrongPass123!", country="Sénégal", role="student",
            first_name="Awa", last_name="Test",
        )
        self.employer = EmployerProfile.objects.create(
            user=self.recruiter, company_name="V78 Africa", country="Sénégal",
            status=EmployerProfile.Status.APPROVED,
        )
        self.talent = CandidateProfile.objects.create(
            user=self.student, headline="Analyste", skills=["Excel"], is_searchable=True,
        )
        Currency.objects.get_or_create(code="EUR", defaults={"name": "Euro", "symbol": "€", "exchange_rate": 1, "is_active": True})
        config = PlatformSettings.load()
        config.employer_free_active_jobs = 1
        config.employer_pro_active_jobs = 5
        config.employer_business_active_jobs = 20
        config.save()
        self.Order = Order

    def activate(self, kind):
        from apps.opportunities.services import activate_employer_entitlement
        order = self.Order.objects.create(
            user=self.recruiter, status=self.Order.Status.PAID,
            provider=self.Order.Provider.MANUAL, provider_sandbox=True,
            base_total_amount="30.34", total_amount="30.34", currency="EUR",
            paid_at=timezone.now(),
        )
        entitlement = activate_employer_entitlement(order, kind=kind)
        return order, entitlement

    def test_starter_cannot_access_talent_pool_but_pro_can(self):
        self.client.force_authenticate(self.recruiter)
        denied = self.client.get("/api/opportunities/talents/")
        self.assertEqual(denied.status_code, 403, denied.data)

        self.activate("pro")
        allowed = self.client.get("/api/opportunities/talents/")
        self.assertEqual(allowed.status_code, 200, allowed.data)
        rows = allowed.data.get("results", allowed.data) if isinstance(allowed.data, dict) else allowed.data
        self.assertTrue(any(row["id"] == self.talent.id for row in rows))

    def test_opt_out_revokes_existing_bookmark_and_hidden_talent_cannot_be_bookmarked(self):
        from .models import TalentBookmark

        self.activate("pro")
        self.client.force_authenticate(self.recruiter)
        created = self.client.post(
            "/api/opportunities/talent-bookmarks/", {"talent": self.talent.id, "note": "prioritaire"}, format="json"
        )
        self.assertEqual(created.status_code, 201, created.data)
        self.assertTrue(TalentBookmark.objects.filter(employer=self.employer, talent=self.talent).exists())

        self.talent.is_searchable = False
        self.talent.save(update_fields=["is_searchable", "updated_at"])
        self.assertFalse(TalentBookmark.objects.filter(employer=self.employer, talent=self.talent).exists())

        rejected = self.client.post(
            "/api/opportunities/talent-bookmarks/", {"talent": self.talent.id}, format="json"
        )
        self.assertEqual(rejected.status_code, 400, rejected.data)

    def test_share_portfolio_false_never_exposes_historical_proof_snapshots(self):
        app = OpportunityApplication.objects.create(
            opportunity=Opportunity.objects.create(
                employer=self.employer, title="Analyste", description="Test", remote_worldwide=True,
                status=Opportunity.Status.PUBLISHED,
            ),
            candidate=self.student,
            candidate_name_snapshot="Awa Test",
            candidate_email_snapshot=self.student.email,
            share_portfolio=False,
            portfolio_snapshot={"slug": "ancien-portfolio"},
            certificates_snapshot=[{"number": "OLD", "verification_code": "legacy", "title": "Ancien cert"}],
            verified_projects_snapshot=[{"title": "Ancien projet"}],
        )
        self.client.force_authenticate(self.recruiter)
        response = self.client.get(f"/api/opportunities/applications/{app.id}/?recruiter=1")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["portfolio_snapshot"], {})
        self.assertEqual(response.data["certificates_snapshot"], [])
        self.assertEqual(response.data["verified_projects_snapshot"], [])

    def test_candidate_can_consult_talent_access_journal(self):
        from .models import TalentAccessLog

        TalentAccessLog.objects.create(
            candidate=self.talent, employer=self.employer, recruiter=self.recruiter,
            access_type=TalentAccessLog.AccessType.PROFILE,
        )
        self.client.force_authenticate(self.student)
        response = self.client.get("/api/opportunities/candidate-profile/talent-accesses/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data[0]["company_name"], "V78 Africa")
        self.assertEqual(response.data[0]["access_type"], "profile")

    def test_recruiter_detail_consultation_is_logged_for_candidate(self):
        from .models import TalentAccessLog

        application = OpportunityApplication.objects.create(
            opportunity=Opportunity.objects.create(
                employer=self.employer, title="Journal", description="Test", remote_worldwide=True,
                status=Opportunity.Status.PUBLISHED,
            ),
            candidate=self.student,
            candidate_name_snapshot="Awa Test",
            candidate_email_snapshot=self.student.email,
        )
        self.client.force_authenticate(self.recruiter)
        response = self.client.get(f"/api/opportunities/applications/{application.id}/?recruiter=1")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(TalentAccessLog.objects.filter(
            candidate=self.talent, employer=self.employer, recruiter=self.recruiter,
            access_type=TalentAccessLog.AccessType.APPLICATION,
        ).exists())

    def test_interview_and_offer_are_visible_to_candidate_and_offer_can_be_accepted(self):
        from datetime import timedelta
        from .models import EmploymentOffer

        job = Opportunity.objects.create(
            employer=self.employer, title="Data Analyst", description="Test", remote_worldwide=True,
            status=Opportunity.Status.PUBLISHED,
        )
        app = OpportunityApplication.objects.create(
            opportunity=job, candidate=self.student,
            candidate_name_snapshot="Awa Test", candidate_email_snapshot=self.student.email,
        )
        self.client.force_authenticate(self.recruiter)
        interview = self.client.post(
            f"/api/opportunities/applications/{app.id}/interviews/",
            {"scheduled_at": (timezone.now() + timedelta(days=2)).isoformat(), "duration_minutes": 45, "mode": "video"},
            format="json",
        )
        self.assertEqual(interview.status_code, 201, interview.data)
        offer = self.client.post(
            f"/api/opportunities/applications/{app.id}/offer/",
            {"title": "Proposition Data Analyst", "message": "Bienvenue", "salary_amount": "1200.00", "salary_currency": "EUR"},
            format="json",
        )
        self.assertEqual(offer.status_code, 201, offer.data)

        self.client.force_authenticate(self.student)
        interviews = self.client.get(f"/api/opportunities/applications/{app.id}/interviews/")
        self.assertEqual(interviews.status_code, 200, interviews.data)
        self.assertEqual(len(interviews.data), 1)
        visible_offer = self.client.get(f"/api/opportunities/applications/{app.id}/offer/")
        self.assertEqual(visible_offer.status_code, 200, visible_offer.data)
        accepted = self.client.post(
            f"/api/opportunities/applications/{app.id}/offer-response/", {"decision": "accepted"}, format="json"
        )
        self.assertEqual(accepted.status_code, 200, accepted.data)
        self.assertEqual(accepted.data["status"], EmploymentOffer.Status.ACCEPTED)
        app.refresh_from_db()
        self.assertEqual(app.status, OpportunityApplication.Status.HIRED)

    def test_rejected_application_cannot_receive_offer(self):
        application = OpportunityApplication.objects.create(
            opportunity=Opportunity.objects.create(
                employer=self.employer, title="Finale", description="Test", remote_worldwide=True,
                status=Opportunity.Status.PUBLISHED,
            ),
            candidate=self.student,
            candidate_name_snapshot="Awa Test",
            candidate_email_snapshot=self.student.email,
            status=OpportunityApplication.Status.REJECTED,
        )
        self.client.force_authenticate(self.recruiter)
        response = self.client.post(
            f"/api/opportunities/applications/{application.id}/offer/",
            {"title": "Offre interdite", "salary_currency": "EUR"},
            format="json",
        )
        self.assertEqual(response.status_code, 409, response.data)
        application.refresh_from_db()
        self.assertEqual(application.status, OpportunityApplication.Status.REJECTED)

    def test_publication_quota_uses_paid_single_post_credit_and_caps_it_to_30_days(self):
        from apps.opportunities.models import EmployerEntitlement
        from apps.opportunities.services import activate_employer_entitlement
        from datetime import timedelta

        Opportunity.objects.create(
            employer=self.employer, title="Offre gratuite", description="Test", remote_worldwide=True,
            status=Opportunity.Status.PUBLISHED,
        )
        self.client.force_authenticate(self.recruiter)
        blocked = self.client.post(
            "/api/opportunities/listings/",
            {"title": "Deuxième offre", "description": "Test", "remote_worldwide": True, "status": "published"},
            format="json",
        )
        self.assertEqual(blocked.status_code, 400, blocked.data)

        order = self.Order.objects.create(
            user=self.recruiter, status=self.Order.Status.PAID, provider=self.Order.Provider.MANUAL,
            provider_sandbox=True, base_total_amount="11.43", total_amount="11.43", currency="EUR", paid_at=timezone.now(),
        )
        entitlement = activate_employer_entitlement(order, kind=EmployerEntitlement.Kind.SINGLE_POST)
        too_long = self.client.post(
            "/api/opportunities/listings/",
            {
                "title": "Annonce trop longue", "description": "Test", "remote_worldwide": True,
                "status": "published", "application_deadline": (timezone.now() + timedelta(days=31)).isoformat(),
            }, format="json",
        )
        self.assertEqual(too_long.status_code, 400, too_long.data)
        entitlement.refresh_from_db()
        self.assertIsNone(entitlement.consumed_at)

        created = self.client.post(
            "/api/opportunities/listings/",
            {"title": "Annonce payée", "description": "Test", "remote_worldwide": True, "status": "published"},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        entitlement.refresh_from_db()
        self.assertIsNotNone(entitlement.consumed_at)
        self.assertEqual(entitlement.consumed_by_id, created.data["id"])
        self.assertLessEqual(entitlement.ends_at, entitlement.starts_at + timedelta(days=30, seconds=1))

        extended = self.client.patch(
            f"/api/opportunities/listings/{created.data['slug']}/",
            {"application_deadline": (timezone.now() + timedelta(days=45)).isoformat()},
            format="json",
        )
        self.assertEqual(extended.status_code, 400, extended.data)
        cleared = self.client.patch(
            f"/api/opportunities/listings/{created.data['slug']}/",
            {"application_deadline": None},
            format="json",
        )
        self.assertEqual(cleared.status_code, 200, cleared.data)
        self.assertIsNotNone(cleared.data["application_deadline"])


class EmployerEntitlementLifecycleV78Tests(APITestCase):
    def setUp(self):
        from apps.payments.models import Currency, Order
        self.recruiter = User.objects.create_user(
            username="v78-life", email="v78-life@example.com", password="StrongPass123!",
            country="Côte d'Ivoire", role="employer",
        )
        self.employer = EmployerProfile.objects.create(
            user=self.recruiter, company_name="Lifecycle SARL", country="Côte d'Ivoire",
            status=EmployerProfile.Status.APPROVED,
        )
        Currency.objects.get_or_create(code="EUR", defaults={"name": "Euro", "symbol": "€", "exchange_rate": 1, "is_active": True})
        self.Order = Order

    def paid_order(self, amount="30.34"):
        return self.Order.objects.create(
            user=self.recruiter, status=self.Order.Status.PAID,
            provider=self.Order.Provider.MANUAL, provider_sandbox=True,
            base_total_amount=amount, total_amount=amount, currency="EUR", paid_at=timezone.now(),
        )

    def test_pro_renewals_chain_and_replay_is_idempotent(self):
        from datetime import timedelta
        from apps.opportunities.services import activate_employer_entitlement

        first_order = self.paid_order()
        first = activate_employer_entitlement(first_order, kind="pro")
        first_end = first.ends_at
        replay = activate_employer_entitlement(first_order, kind="pro")
        self.assertEqual(replay.ends_at, first_end)

        second = activate_employer_entitlement(self.paid_order(), kind="pro")
        self.assertEqual(second.starts_at, first.ends_at)
        self.assertEqual(second.ends_at - second.starts_at, timedelta(days=30))

    def test_refunding_middle_period_shifts_future_renewal_forward_without_gap(self):
        from apps.opportunities.services import activate_employer_entitlement, revoke_employer_entitlement

        first = activate_employer_entitlement(self.paid_order(), kind="business")
        middle_order = self.paid_order("76.07")
        middle = activate_employer_entitlement(middle_order, kind="business")
        last = activate_employer_entitlement(self.paid_order("76.07"), kind="business")
        old_last_start = last.starts_at

        middle_order.status = self.Order.Status.REFUNDED
        middle_order.refunded_at = timezone.now()
        middle_order.save(update_fields=["status", "refunded_at"])
        self.assertTrue(revoke_employer_entitlement(middle_order, reason="Test remboursement"))

        middle.refresh_from_db()
        last.refresh_from_db()
        self.assertIsNotNone(middle.revoked_at)
        self.assertEqual(last.starts_at, middle.starts_at)
        self.assertLess(last.starts_at, old_last_start)
        self.assertEqual(first.ends_at, middle.starts_at)

    def test_refunding_fully_elapsed_period_does_not_extend_following_period(self):
        from apps.opportunities.services import activate_employer_entitlement, revoke_employer_entitlement

        first_order = self.paid_order()
        first = activate_employer_entitlement(first_order, kind="pro")
        second = activate_employer_entitlement(self.paid_order(), kind="pro")
        original_second_start = second.starts_at
        original_second_end = second.ends_at

        # Simule une période déjà consommée intégralement avant le remboursement tardif.
        past_start = timezone.now() - timedelta(days=60)
        past_end = timezone.now() - timedelta(days=30)
        first.starts_at = past_start
        first.ends_at = past_end
        first.save(update_fields=["starts_at", "ends_at", "updated_at"])

        first_order.status = self.Order.Status.REFUNDED
        first_order.refunded_at = timezone.now()
        first_order.save(update_fields=["status", "refunded_at"])
        self.assertTrue(revoke_employer_entitlement(first_order, reason="Remboursement tardif"))

        second.refresh_from_db()
        self.assertEqual(second.starts_at, original_second_start)
        self.assertEqual(second.ends_at, original_second_end)

    def test_refunded_single_post_revokes_credit_and_closes_bound_listing(self):
        from apps.opportunities.services import activate_employer_entitlement, revoke_employer_entitlement
        from apps.opportunities.models import EmployerEntitlement

        order = self.paid_order("11.43")
        entitlement = activate_employer_entitlement(order, kind=EmployerEntitlement.Kind.SINGLE_POST)
        job = Opportunity.objects.create(
            employer=self.employer, title="Annonce remboursée", description="Test", remote_worldwide=True,
            status=Opportunity.Status.PUBLISHED, publication_entitlement=entitlement,
        )
        entitlement.consumed_by = job
        entitlement.consumed_at = timezone.now()
        entitlement.starts_at = timezone.now()
        entitlement.ends_at = timezone.now() + timedelta(days=30)
        entitlement.save(update_fields=["consumed_by", "consumed_at", "starts_at", "ends_at", "updated_at"])

        order.status = self.Order.Status.REFUNDED
        order.refunded_at = timezone.now()
        order.save(update_fields=["status", "refunded_at"])
        self.assertTrue(revoke_employer_entitlement(order, reason="Remboursement annonce"))
        entitlement.refresh_from_db()
        job.refresh_from_db()
        self.assertIsNotNone(entitlement.revoked_at)
        self.assertEqual(job.status, Opportunity.Status.CLOSED)

    @override_settings(TEST_PAYMENTS_ENABLED=True)
    def test_employer_checkout_requires_and_reuses_real_idempotency_key(self):
        from apps.opportunities.models import EmployerEntitlement

        self.client.force_authenticate(self.recruiter)
        no_key = self.client.post(
            "/api/payments/checkout/",
            {"employer_product": "pro", "provider": "manual", "currency": "EUR", "test_payment": True},
            format="json",
        )
        self.assertEqual(no_key.status_code, 400, no_key.data)

        payload = {"employer_product": "pro", "provider": "manual", "currency": "EUR", "test_payment": True}
        first = self.client.post(
            "/api/payments/checkout/", payload, format="json", HTTP_IDEMPOTENCY_KEY="v78-pro-checkout-001"
        )
        self.assertEqual(first.status_code, 201, first.data)
        second = self.client.post(
            "/api/payments/checkout/", payload, format="json", HTTP_IDEMPOTENCY_KEY="v78-pro-checkout-001"
        )
        self.assertEqual(second.status_code, 200, second.data)
        self.assertEqual(first.data["order"]["id"], second.data["order"]["id"])
        self.assertTrue(second.data.get("idempotent_replay"))
        self.assertEqual(EmployerEntitlement.objects.filter(employer=self.employer, kind="pro").count(), 1)
