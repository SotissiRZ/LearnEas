from rest_framework import status
from rest_framework.test import APITestCase, APIClient

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
        self.assertNotIn("refresh", response.data)
        self.assertIn("learneas_refresh", response.cookies)
        self.assertTrue(response.cookies["learneas_refresh"]["httponly"])
        self.assertEqual(response.data["user"]["email"], "student@example.com")
        user = User.objects.get(email="student@example.com")
        self.assertEqual(user.role, User.Role.STUDENT)
        self.assertTrue(user.is_active)

    def test_registration_ignores_django_admin_session_and_does_not_require_csrf(self):
        # Régression : lorsqu’un navigateur avait déjà un cookie de session Django
        # (ex. après connexion à /admin/), SessionAuthentication pouvait imposer un
        # token CSRF au POST public d’inscription. L’API est JWT-only, donc la session
        # Django doit être ignorée par les endpoints REST.
        admin = User.objects.create_user(
            username="csrf_admin",
            email="csrf-admin@example.com",
            password="passpass123",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(admin)
        response = client.post(
            "/api/auth/register/",
            {
                "username": "csrf_student",
                "email": "csrf-student@example.com",
                "country": "Côte d'Ivoire",
                "password": "passpass123",
                "password2": "passpass123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_registration_rejects_case_insensitive_duplicates_cleanly(self):
        User.objects.create_user(username="existing", email="person@example.com", password="passpass123")
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "another",
                "email": "PERSON@EXAMPLE.COM",
                "country": "Sénégal",
                "password": "passpass123",
                "password2": "passpass123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_registration_requires_country_from_reference_list(self):
        missing = self.client.post(
            "/api/auth/register/",
            {
                "email": "no-country@example.com",
                "password": "passpass123",
                "password2": "passpass123",
            },
            format="json",
        )
        self.assertEqual(missing.status_code, status.HTTP_400_BAD_REQUEST, missing.data)
        self.assertIn("country", missing.data)

        invalid = self.client.post(
            "/api/auth/register/",
            {
                "email": "bad-country@example.com",
                "country": "Pays inventé",
                "password": "passpass123",
                "password2": "passpass123",
            },
            format="json",
        )
        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST, invalid.data)
        self.assertIn("country", invalid.data)

    def test_registration_canonicalizes_country_alias(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "email": "rdc@example.com",
                "country": "RDC",
                "password": "passpass123",
                "password2": "passpass123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(User.objects.get(email="rdc@example.com").country, "RD Congo")


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

    def test_public_platform_settings_expose_pricing_without_authentication(self):
        from .models import PlatformSettings
        config = PlatformSettings.load()
        config.instructor_pro_monthly_eur = "15.09"
        config.employer_pro_active_jobs = 5
        config.save()
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/auth/platform-settings/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(response.data["pricing_enabled"])
        self.assertEqual(response.data["platform_commission_percent"], config.platform_commission_percent)
        self.assertEqual(response.data["employer_pro_active_jobs"], 5)
        self.assertIn("instructor_pro_monthly_eur", response.data)

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
                "country": "Sénégal",
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


class InstructorWorkspaceRegressionTests(APITestCase):
    def setUp(self):
        from apps.catalog.models import Category, Course
        from apps.enrollments.models import CourseEnrollment
        from apps.reviews.models import Review

        self.instructor = User.objects.create_user(
            username="instructor_workspace", email="instructor-workspace@example.com",
            password="passpass123", role=User.Role.INSTRUCTOR,
        )
        self.other_instructor = User.objects.create_user(
            username="other_workspace", email="other-workspace@example.com",
            password="passpass123", role=User.Role.INSTRUCTOR,
        )
        self.student = User.objects.create_user(
            username="student_workspace", email="student-workspace@example.com",
            password="passpass123", role=User.Role.STUDENT,
        )
        category = Category.objects.create(name="Workspace")
        self.course = Course.objects.create(
            instructor=self.instructor, category=category, title="Cours instructeur",
            description="Test", published=True,
        )
        other_course = Course.objects.create(
            instructor=self.other_instructor, category=category, title="Cours autre",
            description="Test", published=True,
        )
        CourseEnrollment.objects.create(user=self.student, course=self.course, progress_percent=45)
        Review.objects.create(user=self.student, course=self.course, rating=5, comment="Excellent")
        # Ce contenu ne doit jamais apparaître dans l'espace du premier instructeur.
        CourseEnrollment.objects.create(user=self.student, course=other_course)
        self.client.force_authenticate(self.instructor)

    def test_instructor_overview_and_students_are_scoped_to_owner(self):
        overview = self.client.get("/api/auth/instructor/overview/")
        self.assertEqual(overview.status_code, status.HTTP_200_OK, overview.data)
        self.assertEqual(overview.data["courses"], 1)
        self.assertEqual(overview.data["unique_students"], 1)
        self.assertEqual(overview.data["reviews_count"], 1)

        students = self.client.get("/api/auth/instructor/students/")
        self.assertEqual(students.status_code, status.HTTP_200_OK, students.data)
        self.assertEqual(students.data["unique_students"], 1)
        self.assertEqual(len(students.data["results"]), 1)
        self.assertEqual(students.data["results"][0]["content_title"], self.course.title)

    def test_authenticated_user_can_change_password(self):
        response = self.client.post(
            "/api/auth/change-password/",
            {"current_password": "passpass123", "new_password": "new-pass-1234", "new_password2": "new-pass-1234"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.instructor.refresh_from_db()
        self.assertTrue(self.instructor.check_password("new-pass-1234"))


class HttpOnlyRefreshCookieRegressionTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="cookie_user",
            email="cookie@example.com",
            password="passpass123",
            country="Sénégal",
        )

    def test_login_hides_refresh_from_json_and_sets_httponly_cookie(self):
        response = self.client.post(
            "/api/auth/login/",
            {"email": "cookie@example.com", "password": "passpass123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertIn("access", response.data)
        self.assertNotIn("refresh", response.data)
        cookie = response.cookies.get("learneas_refresh")
        self.assertIsNotNone(cookie)
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["path"], "/api/auth/")

    def test_refresh_reads_httponly_cookie_and_never_returns_refresh_json(self):
        login = self.client.post(
            "/api/auth/login/",
            {"email": "cookie@example.com", "password": "passpass123"},
            format="json",
        )
        old_refresh = login.cookies["learneas_refresh"].value
        response = self.client.post("/api/auth/token/refresh/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertIn("access", response.data)
        self.assertNotIn("refresh", response.data)
        # Avec plusieurs onglets, la rotation à chaque refresh crée une course : le deuxième
        # onglet peut blacklister/supprimer le cookie fraîchement émis au premier. Le refresh
        # HttpOnly reste stable jusqu'au logout/changement de mot de passe.
        if "learneas_refresh" in response.cookies:
            self.assertEqual(response.cookies["learneas_refresh"].value, old_refresh)

    def test_refresh_rejects_unknown_browser_origin(self):
        self.client.post(
            "/api/auth/login/",
            {"email": "cookie@example.com", "password": "passpass123"},
            format="json",
        )
        response = self.client.post(
            "/api/auth/token/refresh/",
            {},
            format="json",
            HTTP_ORIGIN="https://evil.example",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_logout_revokes_refresh_and_deletes_cookie_without_access_token(self):
        self.client.post(
            "/api/auth/login/",
            {"email": "cookie@example.com", "password": "passpass123"},
            format="json",
        )
        response = self.client.post("/api/auth/logout/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        cookie = response.cookies.get("learneas_refresh")
        self.assertIsNotNone(cookie)
        self.assertEqual(cookie["max-age"], 0)

        refresh = self.client.post("/api/auth/token/refresh/", {}, format="json")
        self.assertEqual(refresh.status_code, status.HTTP_401_UNAUTHORIZED)
