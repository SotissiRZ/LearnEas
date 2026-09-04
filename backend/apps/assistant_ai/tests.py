from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.catalog.models import Category, Course, Section, Lesson
from apps.enrollments.models import CourseEnrollment
from .models import AISettings, AIConversation, AIUsage
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
