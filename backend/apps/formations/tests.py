from datetime import timedelta
from decimal import Decimal
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.catalog.models import Category
from .models import InteractiveFormation, FormationEnrollment, FormationSession, FormationAttendance, FormationSignal


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


    def test_instructor_mine_sessions_excludes_sessions_from_other_instructors(self):
        session = FormationSession.objects.create(
            formation=self.formation, session_number=1, scheduled_at=timezone.now(), duration_minutes=75
        )
        other = User.objects.create_user(
            username="other_live_instructor", email="other-live@example.com", password="passpass123",
            role=User.Role.INSTRUCTOR,
        )
        other_formation = InteractiveFormation.objects.create(
            instructor=other, title="Autre atelier", description="Autre", price=0,
            num_sessions=1, session_duration_minutes=60, max_students=5,
        )
        FormationSession.objects.create(
            formation=other_formation, session_number=1, scheduled_at=timezone.now(), duration_minutes=60
        )
        self.client.force_authenticate(self.organizer)
        response = self.client.get("/api/sessions/mine/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        rows = response.data.get("results", response.data)
        self.assertEqual([row["id"] for row in rows], [session.id])
    def _started_session_with_student(self):
        session = FormationSession.objects.create(
            formation=self.formation, session_number=1, scheduled_at=timezone.now(),
            duration_minutes=75, started_at=timezone.now(),
        )
        FormationEnrollment.objects.get_or_create(user=self.student, formation=self.formation)
        self.client.force_authenticate(self.student)
        joined = self.client.post(f"/api/sessions/{session.id}/join/", {}, format="json")
        self.assertEqual(joined.status_code, status.HTTP_201_CREATED, joined.data)
        return session, joined.data["id"]

    def test_live_hand_raise_is_visible_in_presence(self):
        session, attendance_id = self._started_session_with_student()
        raised = self.client.post(
            f"/api/sessions/{session.id}/hand/",
            {"attendance_id": attendance_id, "raised": True},
            format="json",
        )
        self.assertEqual(raised.status_code, status.HTTP_200_OK, raised.data)
        self.assertTrue(raised.data["hand_raised"])

        self.client.force_authenticate(self.organizer)
        presence = self.client.get(f"/api/sessions/{session.id}/presence/")
        self.assertEqual(presence.status_code, status.HTTP_200_OK, presence.data)
        student_row = next(row for row in presence.data if row["user_id"] == self.student.id)
        self.assertTrue(student_row["hand_raised"])

    def test_live_moderation_signal_is_organizer_only(self):
        session, _ = self._started_session_with_student()
        denied = self.client.post(
            f"/api/sessions/{session.id}/signal/",
            {"recipient_id": self.organizer.id, "kind": "control", "payload": {"action": "mute"}},
            format="json",
        )
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN, denied.data)

        self.client.force_authenticate(self.organizer)
        allowed = self.client.post(
            f"/api/sessions/{session.id}/signal/",
            {"recipient_id": self.student.id, "kind": "control", "payload": {"action": "camera_off"}},
            format="json",
        )
        self.assertEqual(allowed.status_code, status.HTTP_201_CREATED, allowed.data)

    def test_live_room_file_upload_list_and_download(self):
        session, _ = self._started_session_with_student()
        with tempfile.TemporaryDirectory() as tmpdir, self.settings(MEDIA_ROOT=tmpdir):
            upload = SimpleUploadedFile("support.pdf", b"fake-pdf-content", content_type="application/pdf")
            created = self.client.post(
                f"/api/sessions/{session.id}/files/", {"file": upload}, format="multipart"
            )
            self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
            self.assertEqual(created.data["name"], "support.pdf")

            listed = self.client.get(f"/api/sessions/{session.id}/files/")
            self.assertEqual(listed.status_code, status.HTTP_200_OK, listed.data)
            self.assertEqual(len(listed.data), 1)

            downloaded = self.client.get(f'/api{created.data["download_path"]}')
            self.assertEqual(downloaded.status_code, status.HTTP_200_OK)
            self.assertIn("attachment", downloaded.get("Content-Disposition", ""))
    def test_shared_code_signal_keeps_latest_state_per_recipient(self):
        session, _ = self._started_session_with_student()
        first = self.client.post(
            f"/api/sessions/{session.id}/signal/",
            {
                "recipient_id": self.organizer.id,
                "kind": "code",
                "payload": {"language": "javascript", "file_name": "main.js", "text": "const a = 1;"},
            },
            format="json",
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED, first.data)
        second = self.client.post(
            f"/api/sessions/{session.id}/signal/",
            {
                "recipient_id": self.organizer.id,
                "kind": "code",
                "payload": {"language": "javascript", "file_name": "main.js", "text": "const a = 2;"},
            },
            format="json",
        )
        self.assertEqual(second.status_code, status.HTTP_201_CREATED, second.data)
        signals = FormationSignal.objects.filter(
            session=session, sender=self.student, recipient=self.organizer, kind=FormationSignal.Kind.CODE
        )
        self.assertEqual(signals.count(), 1)
        self.assertEqual(signals.first().payload["text"], "const a = 2;")

