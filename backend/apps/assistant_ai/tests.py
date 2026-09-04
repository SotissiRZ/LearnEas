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
