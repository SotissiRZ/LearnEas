from datetime import timedelta
from decimal import Decimal
import tempfile

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.test import override_settings

from django.core.files.uploadedfile import SimpleUploadedFile

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.catalog.models import Category
from .models import InteractiveFormation, FormationEnrollment, FormationSession, FormationAttendance, FormationSignal, FormationSessionInvite
from .realtime import load_realtime_ticket, user_group


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
            started_at=timezone.now() - timedelta(minutes=15),
        )
        FormationEnrollment.objects.create(user=self.student, formation=self.formation)
        joined = timezone.now() - timedelta(minutes=12)
        attendance = FormationAttendance.objects.create(
            session=session,
            user=self.student,
            role=FormationAttendance.Role.PARTICIPANT,
            duration_seconds=720,
        )
        ended = joined + timedelta(minutes=12)
        FormationAttendance.objects.filter(id=attendance.id).update(
            joined_at=joined, last_seen_at=ended, left_at=ended, duration_seconds=720
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

    @override_settings(
        RTC_STUN_URL="stun:stun.example.test:3478",
        RTC_TURN_URL="turn:turn.example.test:3478?transport=udp",
        RTC_TURN_SECRET="shared-turn-secret",
        RTC_TURN_TTL_SECONDS=600,
    )
    def test_room_returns_ephemeral_turn_credentials_from_backend(self):
        session, _ = self._started_session_with_student()
        response = self.client.get(f"/api/sessions/{session.id}/room/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        servers = response.data["ice_servers"]
        self.assertEqual(servers[0]["urls"], "stun:stun.example.test:3478")
        turn = servers[1]
        self.assertEqual(turn["urls"], "turn:turn.example.test:3478?transport=udp")
        self.assertTrue(turn["username"].endswith(f":{self.student.id}"))
        self.assertTrue(turn["credential"])
        self.assertNotEqual(turn["credential"], "shared-turn-secret")

    def test_realtime_ticket_is_short_lived_and_scoped_to_user_and_session(self):
        session, _ = self._started_session_with_student()
        response = self.client.post(f"/api/sessions/{session.id}/realtime-ticket/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertLessEqual(response.data["expires_in"], 120)
        payload = load_realtime_ticket(response.data["ticket"])
        self.assertEqual(payload["session_id"], session.id)
        self.assertEqual(payload["user_id"], self.student.id)

    @override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
    def test_signal_is_pushed_to_recipient_realtime_group(self):
        session, _ = self._started_session_with_student()
        layer = get_channel_layer()
        channel_name = async_to_sync(layer.new_channel)("test.realtime.")
        async_to_sync(layer.group_add)(user_group(session.id, self.organizer.id), channel_name)

        response = self.client.post(
            f"/api/sessions/{session.id}/signal/",
            {
                "recipient_id": self.organizer.id,
                "kind": "chat",
                "payload": {"text": "Bonjour realtime"},
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        event = async_to_sync(layer.receive)(channel_name)
        self.assertEqual(event["type"], "signal.message")
        self.assertEqual(event["message"]["kind"], "chat")
        self.assertEqual(event["message"]["payload"]["text"], "Bonjour realtime")

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

    def test_whiteboard_signal_keeps_latest_snapshot(self):
        session, _ = self._started_session_with_student()
        payload = {"strokes": [{"id": "s1", "color": "#10b981", "width": 4, "points": [{"x": 0.1, "y": 0.2}, {"x": 0.2, "y": 0.3}]}]}
        first = self.client.post(
            f"/api/sessions/{session.id}/signal/",
            {"recipient_id": self.organizer.id, "kind": "whiteboard", "payload": payload},
            format="json",
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED, first.data)
        payload["strokes"][0]["points"].append({"x": 0.3, "y": 0.4})
        second = self.client.post(
            f"/api/sessions/{session.id}/signal/",
            {"recipient_id": self.organizer.id, "kind": "whiteboard", "payload": payload},
            format="json",
        )
        self.assertEqual(second.status_code, status.HTTP_201_CREATED, second.data)
        signals = FormationSignal.objects.filter(
            session=session, sender=self.student, recipient=self.organizer, kind=FormationSignal.Kind.WHITEBOARD
        )
        self.assertEqual(signals.count(), 1)
        self.assertEqual(len(signals.first().payload["strokes"][0]["points"]), 3)

    def test_report_does_not_count_time_before_session_start(self):
        session = FormationSession.objects.create(
            formation=self.formation, session_number=1, scheduled_at=timezone.now(), duration_minutes=75,
            started_at=timezone.now() - timedelta(minutes=4), ended_at=timezone.now(), completed=True,
            actual_duration_seconds=240,
        )
        FormationEnrollment.objects.create(user=self.student, formation=self.formation)
        attendance = FormationAttendance.objects.create(
            session=session, user=self.student, role=FormationAttendance.Role.PARTICIPANT,
            duration_seconds=999999,
        )
        # Simule une ancienne ligne corrompue démarrée bien avant la séance.
        joined = session.started_at - timedelta(hours=20)
        FormationAttendance.objects.filter(id=attendance.id).update(
            joined_at=joined, last_seen_at=session.ended_at, left_at=session.ended_at, duration_seconds=999999
        )
        self.client.force_authenticate(self.organizer)
        response = self.client.get(f"/api/sessions/{session.id}/report/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["participants"][0]["total_seconds"], 240)


class FormationSessionInviteTests(APITestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(
            username="invite_org", email="invite-org@example.com", password="passpass123", role=User.Role.INSTRUCTOR
        )
        self.guest = User.objects.create_user(
            username="invite_guest", email="guest@example.com", password="passpass123", role=User.Role.STUDENT
        )
        category = Category.objects.create(name="Invites")
        self.formation = InteractiveFormation.objects.create(
            instructor=self.organizer, category=category, title="Session invités", description="Live",
            price=0, num_sessions=1, session_duration_minutes=60, max_students=10, published=True,
        )
        self.session = FormationSession.objects.create(
            formation=self.formation, session_number=1, scheduled_at=timezone.now(),
            duration_minutes=60, started_at=timezone.now(),
        )

    def test_organizer_can_invite_non_enrolled_student_by_email(self):
        self.client.force_authenticate(self.organizer)
        with self.settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            response = self.client.post(
                f"/api/sessions/{self.session.id}/invites/", {"email": self.guest.email}, format="json"
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(FormationSessionInvite.objects.filter(session=self.session, email=self.guest.email).exists())
        self.assertFalse(FormationEnrollment.objects.filter(user=self.guest, formation=self.formation).exists())

    def test_invited_student_can_access_and_join_without_enrollment(self):
        FormationSessionInvite.objects.create(
            session=self.session, email=self.guest.email, invited_by=self.organizer, invited_user=self.guest
        )
        self.client.force_authenticate(self.guest)
        room = self.client.get(f"/api/sessions/{self.session.id}/room/")
        self.assertEqual(room.status_code, status.HTTP_200_OK, room.data)
        self.assertTrue(room.data["is_guest"])
        joined = self.client.post(f"/api/sessions/{self.session.id}/join/", {}, format="json")
        self.assertEqual(joined.status_code, status.HTTP_201_CREATED, joined.data)
        self.assertEqual(joined.data["role"], FormationAttendance.Role.GUEST)
        self.assertFalse(FormationEnrollment.objects.filter(user=self.guest, formation=self.formation).exists())

    def test_uninvited_non_enrolled_student_cannot_access(self):
        self.client.force_authenticate(self.guest)
        response = self.client.get(f"/api/sessions/{self.session.id}/room/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_revoked_invitation_removes_session_access(self):
        invite = FormationSessionInvite.objects.create(
            session=self.session, email=self.guest.email, invited_by=self.organizer, invited_user=self.guest
        )
        self.client.force_authenticate(self.organizer)
        revoked = self.client.post(f"/api/sessions/{self.session.id}/invites/{invite.id}/revoke/", {}, format="json")
        self.assertEqual(revoked.status_code, status.HTTP_200_OK, revoked.data)
        self.client.force_authenticate(self.guest)
        room = self.client.get(f"/api/sessions/{self.session.id}/room/")
        self.assertEqual(room.status_code, status.HTTP_404_NOT_FOUND)


class CohortAndMentorshipRegressionTests(APITestCase):
    def setUp(self):
        self.mentor = User.objects.create_user(
            username="mentor_regression", email="mentor-regression@example.com", password="passpass123",
            role=User.Role.INSTRUCTOR,
        )
        self.learner = User.objects.create_user(
            username="mentee_regression", email="mentee-regression@example.com", password="passpass123",
            role=User.Role.STUDENT,
        )
        self.category = Category.objects.create(name="Mentorat regression")

    def test_hidden_mentorship_room_never_appears_in_cohort_catalog(self):
        from .models import FormationKind, MentorshipOffering
        from .mentorship import ensure_room_formation

        offer = MentorshipOffering.objects.create(
            instructor=self.mentor,
            title="Portfolio review",
            description="Relecture privée",
            price=Decimal("10.00"),
            published=True,
        )
        room = ensure_room_formation(offer)
        self.assertEqual(room.kind, FormationKind.MENTORSHIP)
        self.assertFalse(room.published)
        self.assertFalse(room.certificate_enabled)

        response = self.client.get("/api/formations/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        rows = response.data.get("results", response.data)
        self.assertNotIn(room.id, [row["id"] for row in rows])

    def test_free_mentorship_booking_confirms_and_grants_only_session_invite(self):
        from .models import MentorshipBooking, MentorshipOffering
        from .mentorship import create_slot

        offer = MentorshipOffering.objects.create(
            instructor=self.mentor,
            title="CV express",
            description="Coaching CV",
            price=Decimal("0.00"),
            published=True,
            booking_notice_hours=1,
        )
        slot = create_slot(offer, timezone.now() + timedelta(days=2))
        self.client.force_authenticate(self.learner)
        booked = self.client.post(
            "/api/mentorship/bookings/",
            {"slot_id": slot.id, "learner_note": "Préparer mon CV"},
            format="json",
        )
        self.assertEqual(booked.status_code, status.HTTP_201_CREATED, booked.data)
        self.assertEqual(booked.data["status"], MentorshipBooking.Status.CONFIRMED)
        self.assertEqual(booked.data["join_session_id"], slot.session_id)
        self.assertTrue(FormationSessionInvite.objects.filter(
            session=slot.session, email__iexact=self.learner.email, revoked_at__isnull=True
        ).exists())
        self.assertFalse(FormationEnrollment.objects.filter(
            user=self.learner, formation=slot.session.formation
        ).exists())

    def test_mentor_can_complete_own_booking_without_as_mentor_query_parameter(self):
        from .models import MentorshipOffering
        from .mentorship import create_slot, reserve_booking

        offer = MentorshipOffering.objects.create(
            instructor=self.mentor,
            title="Entretien technique",
            description="Simulation",
            price=Decimal("0.00"),
            published=True,
            booking_notice_hours=1,
        )
        slot = create_slot(offer, timezone.now() + timedelta(days=2))
        booking = reserve_booking(user=self.learner, slot=slot)
        self.client.force_authenticate(self.mentor)
        response = self.client.post(
            f"/api/mentorship/bookings/{booking.id}/complete/",
            {"mentor_note": "Objectif atteint"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["status"], "completed")
        self.assertEqual(response.data["mentor_note"], "Objectif atteint")

    def test_cohort_deadline_closes_enrollment(self):
        formation = InteractiveFormation.objects.create(
            instructor=self.mentor,
            category=self.category,
            title="Cohorte fermée",
            description="Test date limite",
            price=Decimal("10.00"),
            max_students=10,
            min_students=2,
            enrollment_deadline=timezone.now() - timedelta(minutes=1),
            start_date=(timezone.now() + timedelta(days=1)).date(),
            status="scheduled",
            published=True,
        )
        self.assertFalse(formation.is_enrollment_open)

    def test_historical_mentorship_slot_and_offering_must_be_deactivated_not_deleted(self):
        from .models import MentorshipOffering
        from .mentorship import create_slot, reserve_booking

        offer = MentorshipOffering.objects.create(
            instructor=self.mentor,
            title="Historique mentorat",
            description="Conserver la traçabilité",
            price=Decimal("20.00"),
            published=True,
            booking_notice_hours=1,
        )
        slot = create_slot(offer, timezone.now() + timedelta(days=3))
        reserve_booking(user=self.learner, slot=slot)

        self.client.force_authenticate(self.mentor)
        slot_delete = self.client.delete(f"/api/mentorship/slots/{slot.id}/")
        self.assertEqual(slot_delete.status_code, status.HTTP_409_CONFLICT, slot_delete.data)
        slot.refresh_from_db()

        disabled = self.client.patch(
            f"/api/mentorship/slots/{slot.id}/", {"is_active": False}, format="json"
        )
        self.assertEqual(disabled.status_code, status.HTTP_200_OK, disabled.data)
        self.assertFalse(disabled.data["is_active"])

        offer_delete = self.client.delete(f"/api/mentorship/offerings/{offer.slug}/")
        self.assertEqual(offer_delete.status_code, status.HTTP_409_CONFLICT, offer_delete.data)

        unpublished = self.client.patch(
            f"/api/mentorship/offerings/{offer.slug}/", {"published": False}, format="json"
        )
        self.assertEqual(unpublished.status_code, status.HTTP_200_OK, unpublished.data)
        self.assertFalse(unpublished.data["published"])
