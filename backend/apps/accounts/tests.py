from rest_framework import status
from rest_framework.test import APITestCase

from .models import User


class RegistrationRegressionTests(APITestCase):
    def test_registration_normalizes_email_and_returns_tokens(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "nouvel_etudiant",
                "email": "  Student@Example.COM  ",
                "first_name": "Awa",
                "last_name": "Diallo",
                "country": "Sénégal",
                "password": "motdepasse-solide",
                "password2": "motdepasse-solide",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["email"], "student@example.com")
        user = User.objects.get(email="student@example.com")
        self.assertEqual(user.role, User.Role.STUDENT)
        self.assertTrue(user.is_active)

    def test_registration_rejects_case_insensitive_duplicates_cleanly(self):
        User.objects.create_user(username="existing", email="person@example.com", password="passpass123")
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "another",
                "email": "PERSON@EXAMPLE.COM",
                "password": "passpass123",
                "password2": "passpass123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)


class AdminBackofficeRegressionTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_test", email="admin-test@example.com", password="passpass123",
            role=User.Role.ADMIN, is_staff=True,
        )
        self.student = User.objects.create_user(
            username="student_test", email="student-test@example.com", password="passpass123",
            role=User.Role.STUDENT,
        )
        self.client.force_authenticate(self.admin)

    def test_admin_can_filter_and_update_users(self):
        response = self.client.get("/api/auth/admin/users/?role=student")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        rows = response.data.get("results", response.data)
        self.assertTrue(any(row["id"] == self.student.id for row in rows))

        response = self.client.patch(
            f"/api/auth/admin/users/{self.student.id}/",
            {"role": User.Role.INSTRUCTOR, "is_active": False},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.student.refresh_from_db()
        self.assertEqual(self.student.role, User.Role.INSTRUCTOR)
        self.assertFalse(self.student.is_active)

    def test_platform_settings_disable_registration(self):
        from .models import PlatformSettings
        config = PlatformSettings.load()
        config.registration_enabled = False
        config.save()
        self.client.force_authenticate(user=None)
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "blocked_user",
                "email": "blocked@example.com",
                "password": "passpass123",
                "password2": "passpass123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class InstructorApplicationRegressionTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_app", email="admin-app@example.com", password="passpass123",
            role=User.Role.ADMIN, is_staff=True,
        )
        self.student = User.objects.create_user(
            username="student_app", email="student-app@example.com", password="passpass123",
            role=User.Role.STUDENT,
        )

    def test_application_requires_admin_approval_before_role_change(self):
        self.client.force_authenticate(self.student)
        response = self.client.post(
            "/api/auth/become-instructor/",
            {"domain": "Développement web", "years_experience": 4, "headline": "Développeur senior"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["status"], "pending")
        self.student.refresh_from_db()
        self.assertEqual(self.student.role, User.Role.STUDENT)

        application_id = response.data["id"]
        self.client.force_authenticate(self.admin)
        approve = self.client.post(
            f"/api/auth/admin/instructor-applications/{application_id}/approve/",
            {"review_note": "Profil vérifié"},
            format="json",
        )
        self.assertEqual(approve.status_code, status.HTTP_200_OK, approve.data)
        self.assertEqual(approve.data["status"], "approved")
        self.student.refresh_from_db()
        self.assertEqual(self.student.role, User.Role.INSTRUCTOR)
        self.assertEqual(self.student.domain, "Développement web")

    def test_rejected_application_can_be_resubmitted(self):
        self.client.force_authenticate(self.student)
        first = self.client.post(
            "/api/auth/become-instructor/",
            {"domain": "Design", "years_experience": 1},
            format="json",
        )
        self.client.force_authenticate(self.admin)
        self.client.post(
            f"/api/auth/admin/instructor-applications/{first.data['id']}/reject/",
            {"review_note": "Expérience à préciser"},
            format="json",
        )
        self.client.force_authenticate(self.student)
        second = self.client.post(
            "/api/auth/become-instructor/",
            {"domain": "Design UX", "years_experience": 2, "headline": "UX Designer"},
            format="json",
        )
        self.assertEqual(second.status_code, status.HTTP_201_CREATED, second.data)
        self.assertEqual(second.data["id"], first.data["id"])
        self.assertEqual(second.data["status"], "pending")
