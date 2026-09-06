from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.catalog.models import Category, Course, PDFProduct
from apps.opportunities.models import CandidateProfile

User = get_user_model()


class DiscoverySecurityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.instructor = User.objects.create_user(username="inst-v86", email="inst-v86@example.com", password="testpass123", role="instructor")
        self.category = Category.objects.create(name="Data V86")
        self.course = Course.objects.create(instructor=self.instructor, category=self.category, title="Python Data", description="Analyse de données", published=True)
        self.hidden = Course.objects.create(instructor=self.instructor, category=self.category, title="Python secret", description="Brouillon", published=False)

    def test_global_search_only_exposes_published_catalog(self):
        response = self.client.get("/api/discovery/search/?q=Python&types=course")
        self.assertEqual(response.status_code, 200)
        titles = [row["title"] for row in response.data["groups"]["course"]]
        self.assertIn("Python Data", titles)
        self.assertNotIn("Python secret", titles)

    def test_talents_are_not_searchable_by_anonymous_users(self):
        student = User.objects.create_user(username="talent-v86", email="talent-v86@example.com", password="testpass123", role="student")
        CandidateProfile.objects.create(user=student, headline="Data analyst", is_searchable=True)
        response = self.client.get("/api/discovery/search/?q=Data&types=talent")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("talent", response.data["types"])
        self.assertNotIn("talent", response.data["groups"])

    def test_short_query_is_rejected(self):
        response = self.client.get("/api/discovery/search/?q=a")
        self.assertEqual(response.status_code, 400)
