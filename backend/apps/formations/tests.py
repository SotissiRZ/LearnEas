from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.catalog.models import Category
from .models import InteractiveFormation, FormationEnrollment, FormationSession, FormationAttendance


class InteractiveFormationRegressionTests(APITestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(
            username="organizer", email="organizer@example.com", password="passpass123", role=User.Role.INSTRUCTOR
        )
        self.student = User.objects.create_user(
            username="live_student", email="live@example.com", password="passpass123", role=User.Role.STUDENT
        )
        category = Category.objects.create(name="Live")
        self.formation = InteractiveFormation.objects.create(
            instructor=self.organizer,
            category=category,
            title="Atelier live",
            description="Formation interactive",
            price=Decimal("50.00"),
            num_sessions=2,
            session_duration_minutes=75,
            max_students=10,
            published=True,
        )

    def test_planning_uses_internal_room_and_formation_duration(self):
        self.client.force_authenticate(self.organizer)
        response = self.client.post(
            "/api/sessions/",
            {
                "formation": self.formation.id,
                "session_number": 1,
                "scheduled_at": (timezone.now() + timedelta(days=1)).isoformat(),
                "notes": "Séance 1",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["duration_minutes"], 75)
        self.assertNotIn("meeting_link", response.data)
        session = FormationSession.objects.get(id=response.data["id"])
        self.assertTrue(session.room_key)
        self.assertEqual(session.meeting_link, "")

    def test_attendance_report_tracks_participant_and_duration(self):
        session = FormationSession.objects.create(
            formation=self.formation,
            session_number=1,
            scheduled_at=timezone.now(),
            duration_minutes=75,
        )
        FormationEnrollment.objects.create(user=self.student, formation=self.formation)
        joined = timezone.now() - timedelta(minutes=12)
        FormationAttendance.objects.create(
            session=session,
            user=self.student,
            role=FormationAttendance.Role.PARTICIPANT,
            joined_at=joined,
            last_seen_at=timezone.now(),
            left_at=timezone.now(),
            duration_seconds=720,
        )
        self.client.force_authenticate(self.organizer)
        response = self.client.get(f"/api/sessions/{session.id}/report/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["organizers"][0]["id"], self.organizer.id)
        self.assertEqual(response.data["participants"][0]["user_id"], self.student.id)
        self.assertEqual(response.data["participants"][0]["total_seconds"], 720)
    def test_participant_waits_until_organizer_starts_session(self):
        session = FormationSession.objects.create(
            formation=self.formation, session_number=1, scheduled_at=timezone.now(), duration_minutes=75
        )
        FormationEnrollment.objects.create(user=self.student, formation=self.formation)
        self.client.force_authenticate(self.student)
        waiting = self.client.post(f"/api/sessions/{session.id}/join/", {}, format="json")
        self.assertEqual(waiting.status_code, status.HTTP_409_CONFLICT, waiting.data)

        self.client.force_authenticate(self.organizer)
        started = self.client.post(f"/api/sessions/{session.id}/start/", {}, format="json")
        self.assertEqual(started.status_code, status.HTTP_200_OK, started.data)

        self.client.force_authenticate(self.student)
        joined = self.client.post(f"/api/sessions/{session.id}/join/", {}, format="json")
        self.assertEqual(joined.status_code, status.HTTP_201_CREATED, joined.data)

