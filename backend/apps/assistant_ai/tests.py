from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.catalog.models import Category, Course, Section, Lesson
from apps.enrollments.models import CourseEnrollment
from .models import AISettings, AIConversation, AIUsage, AIEvaluationCase, AIKnowledgeChunk
from .rag import index_course, index_lesson


@override_settings(AI_DRY_RUN=True, AI_INDEX_ASYNC=False)
class AssistantAITests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(username="ai-student", email="ai-student@example.com", password="pass1234", role="student")
        self.instructor = User.objects.create_user(username="ai-teacher", email="ai-teacher@example.com", password="pass1234", role="instructor")
        self.category = Category.objects.create(name="IA Test")
        self.course = Course.objects.create(instructor=self.instructor, category=self.category, title="Python pratique", description="Apprendre les listes et dictionnaires Python.", published=True)
        self.section = Section.objects.create(course=self.course, title="Bases")
        self.lesson = Lesson.objects.create(section=self.section, title="Les listes", transcript="Une liste Python stocke plusieurs éléments ordonnés.", is_preview=False)
        index_course(self.course)
        index_lesson(self.lesson)
        self.client = APIClient()
        self.client.force_authenticate(self.student)
        self.cfg = AISettings.load()

    def test_status_exposes_quota_without_secret(self):
        response = self.client.get("/api/ai/status/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("quota", response.data)
        self.assertNotIn("api_key", response.data)

    def test_chat_persists_conversation_and_usage(self):
        CourseEnrollment.objects.create(user=self.student, course=self.course)
        response = self.client.post("/api/ai/chat/", {
            "message": "Explique les listes Python",
            "page_context": {"path": f"/learn/{self.course.slug}", "course_slug": self.course.slug, "lesson_id": self.lesson.id},
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["message"]["content"])
        self.assertTrue(response.data["message"]["sources"])
        self.assertEqual(AIConversation.objects.filter(user=self.student).count(), 1)
        self.assertEqual(AIUsage.objects.filter(user=self.student).count(), 1)

    def test_private_lesson_not_exposed_without_enrollment(self):
        response = self.client.post("/api/ai/chat/", {
            "message": "Que dit la leçon sur les listes ?",
            "page_context": {"course_slug": self.course.slug, "lesson_id": self.lesson.id},
        }, format="json")
        self.assertEqual(response.status_code, 200)
        source_types = {s["type"] for s in response.data["message"]["sources"]}
        self.assertNotIn("lesson", source_types)

    def test_monthly_quota_is_enforced(self):
        self.cfg.student_monthly_limit = 1
        self.cfg.save()
        first = self.client.post("/api/ai/chat/", {"message": "Bonjour"}, format="json")
        self.assertEqual(first.status_code, 200)
        second = self.client.post("/api/ai/chat/", {"message": "Encore"}, format="json")
        self.assertEqual(second.status_code, 429)


    def test_history_can_be_hidden_and_not_reused(self):
        self.cfg.history_enabled = False
        self.cfg.save()
        first = self.client.post("/api/ai/chat/", {"message": "Première question"}, format="json")
        self.assertEqual(first.status_code, 200)
        listing = self.client.get("/api/ai/conversations/")
        self.assertEqual(listing.status_code, 200)
        payload = listing.data.get("results", listing.data) if hasattr(listing.data, "get") else listing.data
        self.assertEqual(len(payload), 0)

    def test_user_cannot_read_another_users_conversation(self):
        other = User.objects.create_user(username="other-ai", email="other-ai@example.com", password="pass1234")
        conversation = AIConversation.objects.create(user=other, title="Privé")
        response = self.client.get(f"/api/ai/conversations/{conversation.id}/")
        self.assertEqual(response.status_code, 404)

    def test_feedback_is_scoped_to_message_owner(self):
        first = self.client.post("/api/ai/chat/", {"message": "Bonjour"}, format="json")
        self.assertEqual(first.status_code, 200)
        message_id = first.data["message"]["id"]
        feedback = self.client.post(f"/api/ai/messages/{message_id}/feedback/", {"feedback": "helpful"}, format="json")
        self.assertEqual(feedback.status_code, 200)
        self.assertEqual(feedback.data["feedback"], "helpful")

        other = User.objects.create_user(username="feedback-other", email="feedback-other@example.com", password="pass1234")
        other_client = APIClient()
        other_client.force_authenticate(other)
        forbidden = other_client.post(f"/api/ai/messages/{message_id}/feedback/", {"feedback": "unhelpful"}, format="json")
        self.assertEqual(forbidden.status_code, 404)

    def test_usage_cost_is_computed_from_admin_rates(self):
        from decimal import Decimal
        from .services import estimate_cost_eur
        self.cfg.input_cost_per_million_eur = Decimal("2")
        self.cfg.output_cost_per_million_eur = Decimal("8")
        self.cfg.save()
        self.assertEqual(estimate_cost_eur(500000, 250000, self.cfg), Decimal("3.000000"))

    def test_explicit_query_does_not_force_unrelated_page_chunk(self):
        CourseEnrollment.objects.create(user=self.student, course=self.course)
        other_course = Course.objects.create(
            instructor=self.instructor, category=self.category, title="Design graphique", description="Couleurs et typographie.", published=True
        )
        index_course(other_course)
        response = self.client.post("/api/ai/chat/", {
            "message": "Que dit KalanPro sur les dictionnaires Python ?",
            "page_context": {"course_slug": other_course.slug},
        }, format="json")
        self.assertEqual(response.status_code, 200)
        titles = [source["title"] for source in response.data["message"]["sources"]]
        self.assertTrue(any("Python" in title for title in titles))

    def test_admin_can_run_rag_evaluation(self):
        admin = User.objects.create_user(username="ai-admin", email="ai-admin@example.com", password="pass1234", role="admin")
        AIEvaluationCase.objects.create(
            question="Que contient la leçon Les listes ?",
            expected_source_type=AIKnowledgeChunk.SourceType.LESSON,
            expected_source_id=self.lesson.id,
        )
        client = APIClient()
        client.force_authenticate(admin)
        response = client.post("/api/ai/admin/evaluate-rag/", {"seed": False, "top_k": 6}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total"], 1)
        self.assertEqual(response.data["passed"], 1)

    def test_catalog_tool_returns_published_courses(self):
        from .tools import execute_read_tool
        result = execute_read_tool(self.student, "search_learning_catalog", {"query": "Python", "kind": "course", "limit": 5})
        self.assertTrue(any(item["id"] == self.course.id for item in result["items"]))

    def test_confirmed_wishlist_action_executes_only_for_owner(self):
        from .models import AIMessage
        from .tools import create_action_proposal
        conversation = AIConversation.objects.create(user=self.student, title="Action")
        message = AIMessage.objects.create(conversation=conversation, role="assistant", content="Je peux l'ajouter.")
        action = create_action_proposal(self.student, conversation, message, "add_course_to_wishlist", {"course_id": self.course.id})
        response = self.client.post(f"/api/ai/actions/{action.confirmation_token}/confirm/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.student.wishlist.filter(course=self.course).exists())

        other = User.objects.create_user(username="action-other", email="action-other@example.com", password="pass1234")
        other_client = APIClient()
        other_client.force_authenticate(other)
        forbidden = other_client.post(f"/api/ai/actions/{action.confirmation_token}/confirm/", {}, format="json")
        self.assertEqual(forbidden.status_code, 404)

    def test_instructor_can_confirm_quiz_draft(self):
        from .models import AIMessage, AIDraft
        from .tools import create_action_proposal
        client = APIClient()
        client.force_authenticate(self.instructor)
        conversation = AIConversation.objects.create(user=self.instructor, title="Quiz")
        message = AIMessage.objects.create(conversation=conversation, role="assistant", content="Quiz prêt.")
        action = create_action_proposal(self.instructor, conversation, message, "save_quiz_draft", {
            "title": "Quiz Python",
            "course_id": self.course.id,
            "questions": [{"question": "Quel type stocke plusieurs éléments ?", "options": ["Liste", "Entier"], "correct_answer": "Liste", "explanation": "Une liste contient plusieurs éléments."}],
        })
        response = client.post(f"/api/ai/actions/{action.confirmation_token}/confirm/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(AIDraft.objects.filter(user=self.instructor, kind="quiz", title="Quiz Python").exists())

    def test_student_cannot_prepare_instructor_draft(self):
        from .models import AIMessage
        from .tools import create_action_proposal
        conversation = AIConversation.objects.create(user=self.student, title="Nope")
        message = AIMessage.objects.create(conversation=conversation, role="assistant", content="")
        with self.assertRaises(PermissionError):
            create_action_proposal(self.student, conversation, message, "save_course_outline_draft", {
                "title": "Cours interdit", "sections": [{"title": "A", "lessons": ["B"]}],
            })

    def test_instructor_can_create_real_unpublished_course_draft(self):
        from .models import AIMessage
        from .tools import create_action_proposal
        client = APIClient()
        client.force_authenticate(self.instructor)
        conversation = AIConversation.objects.create(user=self.instructor, title="Cours réel")
        message = AIMessage.objects.create(conversation=conversation, role="assistant", content="Cours prêt à créer.")
        action = create_action_proposal(self.instructor, conversation, message, "create_course_draft", {
            "title": "Django de zéro à API",
            "description": "Un parcours progressif pour construire une API Django.",
            "level": "beginner",
            "language": "Français",
            "category_id": self.category.id,
            "what_you_will_learn": ["Créer des modèles", "Construire une API"],
            "sections": [
                {"title": "Fondations", "lessons": [{"title": "Installer Django", "description": "Préparer le projet."}, {"title": "Premier modèle"}]},
                {"title": "API", "lessons": [{"title": "Serializers et vues"}]},
            ],
        })
        response = client.post(f"/api/ai/actions/{action.confirmation_token}/confirm/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        created = Course.objects.get(title="Django de zéro à API")
        self.assertFalse(created.published)
        self.assertEqual(created.instructor, self.instructor)
        self.assertEqual(created.sections.count(), 2)
        self.assertEqual(Lesson.objects.filter(section__course=created).count(), 3)

    def test_student_can_confirm_internal_opportunity_application(self):
        from apps.opportunities.models import EmployerProfile, Opportunity, OpportunityApplication
        from .models import AIMessage
        from .tools import create_action_proposal
        employer_user = User.objects.create_user(username="employer-ai", email="employer-ai@example.com", password="pass1234")
        employer = EmployerProfile.objects.create(
            user=employer_user, company_name="Kalan Tech", country="Sénégal", status=EmployerProfile.Status.APPROVED
        )
        opportunity = Opportunity.objects.create(
            employer=employer, title="Développeur Python Junior", description="Construire des APIs Python.",
            skills_required=["Python", "Django"], status=Opportunity.Status.PUBLISHED,
            apply_mode=Opportunity.ApplyMode.INTERNAL,
        )
        conversation = AIConversation.objects.create(user=self.student, title="Candidature")
        message = AIMessage.objects.create(conversation=conversation, role="assistant", content="Candidature prête.")
        action = create_action_proposal(self.student, conversation, message, "submit_opportunity_application", {
            "opportunity_id": opportunity.id,
            "cover_letter": "Je souhaite rejoindre votre équipe pour contribuer sur Django.",
            "share_portfolio": True,
        })
        response = self.client.post(f"/api/ai/actions/{action.confirmation_token}/confirm/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        application = OpportunityApplication.objects.get(opportunity=opportunity, candidate=self.student)
        self.assertEqual(application.status, OpportunityApplication.Status.SUBMITTED)
        self.assertIn("Django", application.cover_letter)

    def test_cv_fit_tool_reports_missing_required_skills(self):
        from apps.opportunities.models import CandidateProfile, EmployerProfile, Opportunity
        from .tools import execute_read_tool
        CandidateProfile.objects.create(user=self.student, skills=["Python"], desired_roles=["Développeur"], years_experience=1)
        employer_user = User.objects.create_user(username="fit-employer", email="fit-employer@example.com", password="pass1234")
        employer = EmployerProfile.objects.create(user=employer_user, company_name="Data Fit", country="Côte d'Ivoire", status=EmployerProfile.Status.APPROVED)
        opportunity = Opportunity.objects.create(
            employer=employer, title="Développeur Data", description="Python et SQL requis.",
            skills_required=["Python", "SQL"], status=Opportunity.Status.PUBLISHED,
        )
        result = execute_read_tool(self.student, "analyze_my_cv_against_opportunity", {"opportunity_id": opportunity.id})
        self.assertIn("Python", result["analysis"]["matched_required_skills"])
        self.assertIn("SQL", result["analysis"]["missing_required_skills"])

    def test_mentor_can_save_private_session_plan(self):
        from datetime import timedelta
        from django.utils import timezone
        from apps.formations.models import MentorshipOffering, MentorshipSlot, MentorshipBooking
        from .models import AIMessage, AIDraft
        from .tools import create_action_proposal
        offering = MentorshipOffering.objects.create(
            instructor=self.instructor, title="Mentorat Django", description="Accompagnement 1:1", published=True
        )
        slot = MentorshipSlot.objects.create(offering=offering, starts_at=timezone.now() + timedelta(days=1))
        booking = MentorshipBooking.objects.create(
            user=self.student, offering=offering, slot=slot, status=MentorshipBooking.Status.CONFIRMED
        )
        client = APIClient()
        client.force_authenticate(self.instructor)
        conversation = AIConversation.objects.create(user=self.instructor, title="Mentorat")
        message = AIMessage.objects.create(conversation=conversation, role="assistant", content="Plan prêt.")
        action = create_action_proposal(self.instructor, conversation, message, "save_mentorship_plan_draft", {
            "booking_id": booking.id, "title": "Préparation séance Django",
            "objectives": ["Clarifier le projet"], "agenda": ["Diagnostic", "Plan d'action"],
            "questions": ["Quel est le principal blocage ?"], "follow_up": ["Créer une petite API"],
        })
        response = client.post(f"/api/ai/actions/{action.confirmation_token}/confirm/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(AIDraft.objects.filter(user=self.instructor, kind=AIDraft.Kind.MENTOR_PLAN).exists())

    def test_recruiter_can_shortlist_only_own_application_with_confirmation(self):
        from apps.opportunities.models import EmployerProfile, Opportunity, OpportunityApplication
        from apps.opportunities.services import build_application_snapshot
        from .models import AIMessage
        from .tools import create_action_proposal
        recruiter = User.objects.create_user(username="recruiter-ai", email="recruiter-ai@example.com", password="pass1234")
        employer = EmployerProfile.objects.create(user=recruiter, company_name="Talent K", country="Maroc", status=EmployerProfile.Status.APPROVED)
        opportunity = Opportunity.objects.create(employer=employer, title="Analyste", description="Analyse de données", status=Opportunity.Status.PUBLISHED)
        snapshot = build_application_snapshot(self.student, opportunity, share_portfolio=False)
        application = OpportunityApplication.objects.create(opportunity=opportunity, candidate=self.student, share_portfolio=False, **snapshot)
        client = APIClient()
        client.force_authenticate(recruiter)
        conversation = AIConversation.objects.create(user=recruiter, title="Shortlist")
        message = AIMessage.objects.create(conversation=conversation, role="assistant", content="Je propose une shortlist.")
        action = create_action_proposal(recruiter, conversation, message, "update_application_stage", {
            "application_id": application.id, "status": "shortlisted", "recruiter_note": "Profil à rencontrer."
        })
        response = client.post(f"/api/ai/actions/{action.confirmation_token}/confirm/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        application.refresh_from_db()
        self.assertEqual(application.status, OpportunityApplication.Status.SHORTLISTED)
        self.assertEqual(application.recruiter_note, "Profil à rencontrer.")

    def test_dry_run_can_prepare_application_confirmation_from_opportunity_context(self):
        from apps.opportunities.models import EmployerProfile, Opportunity
        employer_user = User.objects.create_user(username="dry-employer", email="dry-employer@example.com", password="pass1234")
        employer = EmployerProfile.objects.create(user=employer_user, company_name="Dry Run SARL", country="Sénégal", status=EmployerProfile.Status.APPROVED)
        opportunity = Opportunity.objects.create(
            employer=employer, title="Développeur API", description="API Django", status=Opportunity.Status.PUBLISHED,
            apply_mode=Opportunity.ApplyMode.INTERNAL,
        )
        response = self.client.post("/api/ai/chat/", {
            "message": "Je veux candidater à cette offre",
            "page_context": {"path": f"/opportunities/{opportunity.slug}", "opportunity_slug": opportunity.slug},
        }, format="json")
        self.assertEqual(response.status_code, 200)
        actions = response.data["message"].get("actions") or []
        self.assertTrue(actions)
        self.assertEqual(actions[0]["tool"], "submit_opportunity_application")
        self.assertEqual(actions[0]["status"], "proposed")
