from datetime import time, timedelta
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

    def test_organizer_can_update_session_schedule_and_duration(self):
        session = FormationSession.objects.create(
            formation=self.formation,
            session_number=1,
            scheduled_at=timezone.now() + timedelta(days=1),
            duration_minutes=75,
        )
        new_date = timezone.now() + timedelta(days=3)
        self.client.force_authenticate(self.organizer)
        response = self.client.patch(
            f"/api/sessions/{session.id}/",
            {"scheduled_at": new_date.isoformat(), "duration_minutes": 105},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        session.refresh_from_db()
        self.assertEqual(session.duration_minutes, 105)
        self.assertLess(abs((session.scheduled_at - new_date).total_seconds()), 1)

    def test_student_cannot_update_session_schedule(self):
        session = FormationSession.objects.create(
            formation=self.formation, session_number=1,
            scheduled_at=timezone.now() + timedelta(days=1), duration_minutes=75,
        )
        FormationEnrollment.objects.create(user=self.student, formation=self.formation)
        self.client.force_authenticate(self.student)
        response = self.client.patch(
            f"/api/sessions/{session.id}/",
            {"scheduled_at": (timezone.now() + timedelta(days=2)).isoformat()},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_started_session_schedule_is_locked(self):
        session = FormationSession.objects.create(
            formation=self.formation, session_number=1,
            scheduled_at=timezone.now(), duration_minutes=75, started_at=timezone.now(),
        )
        self.client.force_authenticate(self.organizer)
        response = self.client.patch(
            f"/api/sessions/{session.id}/",
            {"duration_minutes": 120},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)

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

    def test_participant_can_signal_own_screen_share_state(self):
        session, _ = self._started_session_with_student()
        response = self.client.post(
            f"/api/sessions/{session.id}/signal/",
            {
                "recipient_id": self.organizer.id,
                "kind": "control",
                "payload": {"action": "screen_share_state", "active": True},
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        signal = FormationSignal.objects.get(id=response.data["id"])
        self.assertEqual(signal.sender_id, self.student.id)
        self.assertEqual(signal.payload["action"], "screen_share_state")
        self.assertTrue(signal.payload["active"])

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

    def test_waitlist_offers_oldest_user_when_seat_is_released(self):
        from .cohorts import join_waitlist, refresh_waitlist
        from .models import FormationWaitlistEntry

        holder = User.objects.create_user(
            username="cohort_holder", email="holder@example.com", password="passpass123", role=User.Role.STUDENT
        )
        second = User.objects.create_user(
            username="cohort_second", email="second@example.com", password="passpass123", role=User.Role.STUDENT
        )
        formation = InteractiveFormation.objects.create(
            instructor=self.mentor, category=self.category, title="Cohorte attente", description="Liste",
            price=Decimal("25.00"), max_students=1, status="scheduled", published=True,
            start_date=(timezone.now() + timedelta(days=10)).date(),
        )
        enrollment = FormationEnrollment.objects.create(user=holder, formation=formation)
        first_entry = join_waitlist(self.learner, formation)
        join_waitlist(second, formation)
        self.assertEqual(first_entry.status, FormationWaitlistEntry.Status.WAITING)

        enrollment.revoked_at = timezone.now()
        enrollment.save(update_fields=["revoked_at"])
        refresh_waitlist(formation.id)
        first_entry.refresh_from_db()
        second_entry = FormationWaitlistEntry.objects.get(formation=formation, user=second)
        self.assertEqual(first_entry.status, FormationWaitlistEntry.Status.OFFERED)
        self.assertEqual(second_entry.status, FormationWaitlistEntry.Status.WAITING)
        self.assertIsNotNone(first_entry.offer_expires_at)

    def test_expired_waitlist_offer_moves_to_next_user(self):
        from .cohorts import join_waitlist, refresh_waitlist
        from .models import FormationWaitlistEntry

        second = User.objects.create_user(
            username="waitlist_next", email="waitlist-next@example.com", password="passpass123", role=User.Role.STUDENT
        )
        formation = InteractiveFormation.objects.create(
            instructor=self.mentor, category=self.category, title="Cohorte expiration", description="Liste",
            price=Decimal("0.00"), max_students=1, status="scheduled", published=True,
            start_date=(timezone.now() + timedelta(days=10)).date(),
        )
        first = join_waitlist(self.learner, formation)
        join_waitlist(second, formation)
        first.refresh_from_db()
        self.assertEqual(first.status, FormationWaitlistEntry.Status.OFFERED)
        FormationWaitlistEntry.objects.filter(pk=first.pk).update(offer_expires_at=timezone.now() - timedelta(minutes=1))
        refresh_waitlist(formation.id)
        first.refresh_from_db()
        second_entry = FormationWaitlistEntry.objects.get(formation=formation, user=second)
        self.assertEqual(first.status, FormationWaitlistEntry.Status.EXPIRED)
        self.assertEqual(second_entry.status, FormationWaitlistEntry.Status.OFFERED)

    def test_mentorship_pass_confirms_booking_and_cancel_restores_credit(self):
        from .models import MentorshipOffering, MentorshipPack, MentorshipPass
        from .mentorship import create_slot

        offer = MentorshipOffering.objects.create(
            instructor=self.mentor, title="Pack coaching", description="Pack", price=Decimal("30.00"),
            published=True, booking_notice_hours=1, cancellation_notice_hours=12,
        )
        pack = MentorshipPack.objects.create(offering=offer, sessions_count=3, price=Decimal("75.00"), validity_days=90)
        pass_obj = MentorshipPass.objects.create(
            user=self.learner, pack=pack, total_sessions=3, remaining_sessions=3,
            expires_at=timezone.now() + timedelta(days=90),
        )
        slot = create_slot(offer, timezone.now() + timedelta(days=3))
        self.client.force_authenticate(self.learner)
        booked = self.client.post(
            "/api/mentorship/bookings/", {"slot_id": slot.id, "pass_id": pass_obj.id}, format="json"
        )
        self.assertEqual(booked.status_code, status.HTTP_201_CREATED, booked.data)
        self.assertEqual(booked.data["status"], "confirmed")
        self.assertEqual(booked.data["price_snapshot"], "0.00")
        pass_obj.refresh_from_db()
        self.assertEqual(pass_obj.remaining_sessions, 2)

        cancelled = self.client.post(f"/api/mentorship/bookings/{booked.data['id']}/cancel/", {}, format="json")
        self.assertEqual(cancelled.status_code, status.HTTP_200_OK, cancelled.data)
        pass_obj.refresh_from_db()
        self.assertEqual(pass_obj.remaining_sessions, 3)

    def test_confirmed_mentorship_booking_can_be_rescheduled_without_second_payment(self):
        from .models import MentorshipOffering, MentorshipBooking
        from .mentorship import create_slot, reserve_booking

        offer = MentorshipOffering.objects.create(
            instructor=self.mentor, title="Reprogrammation", description="Test", price=Decimal("0.00"),
            published=True, booking_notice_hours=1, cancellation_notice_hours=12,
        )
        first_slot = create_slot(offer, timezone.now() + timedelta(days=3))
        second_slot = create_slot(offer, timezone.now() + timedelta(days=4))
        booking = reserve_booking(user=self.learner, slot=first_slot)
        self.assertEqual(booking.status, MentorshipBooking.Status.CONFIRMED)

        self.client.force_authenticate(self.learner)
        response = self.client.post(
            f"/api/mentorship/bookings/{booking.id}/reschedule/", {"slot_id": second_slot.id}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        booking.refresh_from_db()
        self.assertEqual(booking.slot_id, second_slot.id)
        self.assertEqual(booking.reschedule_count, 1)
        self.assertTrue(FormationSessionInvite.objects.filter(
            session=second_slot.session, invited_user=self.learner, revoked_at__isnull=True
        ).exists())
        self.assertFalse(FormationSessionInvite.objects.filter(
            session=first_slot.session, invited_user=self.learner, revoked_at__isnull=True
        ).exists())

    def test_recurring_availability_rule_generates_future_slots(self):
        from zoneinfo import ZoneInfo
        from .models import MentorshipAvailabilityRule, MentorshipOffering
        from .mentorship import generate_rule_slots

        offer = MentorshipOffering.objects.create(
            instructor=self.mentor, title="Récurrent", description="Test", price=Decimal("0.00"),
            published=True, timezone="UTC", booking_notice_hours=0, duration_minutes=30,
        )
        target = timezone.now().astimezone(ZoneInfo("UTC")).date() + timedelta(days=2)
        while target.weekday() != 0:
            target += timedelta(days=1)
        rule = MentorshipAvailabilityRule.objects.create(
            offering=offer, weekday=0, start_time=time(9, 0), end_time=time(11, 0), interval_minutes=30,
            valid_from=target, valid_until=target,
        )
        created = generate_rule_slots(rule, horizon_days=10)
        self.assertEqual(created, 4)
        self.assertEqual(offer.slots.filter(starts_at__date=target).count(), 4)
        self.assertEqual(offer.slots.filter(availability_rule=rule).count(), 4)

        rule.is_active = False
        rule.save(update_fields=["is_active"])
        generate_rule_slots(rule, horizon_days=10)
        self.assertEqual(offer.slots.filter(availability_rule=rule, is_active=True).count(), 0)

    def test_expired_waitlist_user_can_rejoin_with_one_action(self):
        from .cohorts import join_waitlist
        from .models import FormationWaitlistEntry

        formation = InteractiveFormation.objects.create(
            instructor=self.mentor, category=self.category, title="Cohorte réinscription", description="Liste",
            price=Decimal("0.00"), max_students=1, status="scheduled", published=True,
            start_date=(timezone.now() + timedelta(days=10)).date(),
        )
        entry = join_waitlist(self.learner, formation)
        self.assertEqual(entry.status, FormationWaitlistEntry.Status.OFFERED)
        FormationWaitlistEntry.objects.filter(pk=entry.pk).update(offer_expires_at=timezone.now() - timedelta(minutes=1))
        rejoined = join_waitlist(self.learner, formation)
        self.assertIn(rejoined.status, {FormationWaitlistEntry.Status.WAITING, FormationWaitlistEntry.Status.OFFERED})
        self.assertNotEqual(rejoined.status, FormationWaitlistEntry.Status.EXPIRED)

    def test_mentor_cannot_accept_overlapping_bookings_across_offers(self):
        from .models import MentorshipOffering
        from .mentorship import create_slot, reserve_booking

        second_learner = User.objects.create_user(
            username="mentor_overlap_student", email="overlap@example.com", password="passpass123", role=User.Role.STUDENT
        )
        offer_a = MentorshipOffering.objects.create(
            instructor=self.mentor, title="Overlap A", description="A", duration_minutes=60,
            price=Decimal("0.00"), published=True, booking_notice_hours=0,
        )
        offer_b = MentorshipOffering.objects.create(
            instructor=self.mentor, title="Overlap B", description="B", duration_minutes=60,
            price=Decimal("0.00"), published=True, booking_notice_hours=0,
        )
        starts = timezone.now() + timedelta(days=2)
        first = create_slot(offer_a, starts)
        overlapping = create_slot(offer_b, starts + timedelta(minutes=30))
        reserve_booking(user=self.learner, slot=first)
        with self.assertRaisesMessage(ValueError, "plage horaire"):
            reserve_booking(user=second_learner, slot=overlapping)

    def test_pack_session_must_happen_before_pass_expiry(self):
        from .models import MentorshipOffering, MentorshipPack, MentorshipPass
        from .mentorship import create_slot, reserve_booking

        offer = MentorshipOffering.objects.create(
            instructor=self.mentor, title="Pack validité", description="Pack", duration_minutes=30,
            price=Decimal("20.00"), published=True, booking_notice_hours=0,
        )
        pack = MentorshipPack.objects.create(offering=offer, sessions_count=2, price=Decimal("30.00"), validity_days=7)
        pass_obj = MentorshipPass.objects.create(
            user=self.learner, pack=pack, total_sessions=2, remaining_sessions=2,
            expires_at=timezone.now() + timedelta(days=3),
        )
        late_slot = create_slot(offer, timezone.now() + timedelta(days=5))
        with self.assertRaisesMessage(ValueError, "date de validité"):
            reserve_booking(user=self.learner, slot=late_slot, mentorship_pass=pass_obj)

    def test_instructor_waitlist_endpoint_is_private_and_exposes_no_email(self):
        from .cohorts import join_waitlist

        formation = InteractiveFormation.objects.create(
            instructor=self.mentor, category=self.category, title="Cohorte pilotage", description="Liste",
            price=Decimal("0.00"), max_students=1, status="scheduled", published=True,
            start_date=(timezone.now() + timedelta(days=10)).date(),
        )
        holder = User.objects.create_user(
            username="wait_holder", email="wait-holder@example.com", password="passpass123", role=User.Role.STUDENT
        )
        FormationEnrollment.objects.create(user=holder, formation=formation)
        join_waitlist(self.learner, formation)

        self.client.force_authenticate(self.mentor)
        response = self.client.get(f"/api/formations/{formation.slug}/waitlist/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["waiting"], 1)
        self.assertEqual(response.data["results"][0]["user"]["id"], self.learner.id)
        self.assertNotIn("email", response.data["results"][0]["user"])

        self.client.force_authenticate(self.learner)
        forbidden = self.client.get(f"/api/formations/{formation.slug}/waitlist/")
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN, forbidden.data)

    def test_availability_rules_cannot_overlap_on_same_offer(self):
        from .models import MentorshipAvailabilityRule, MentorshipOffering
        from .serializers import MentorshipAvailabilityRuleSerializer

        offer = MentorshipOffering.objects.create(
            instructor=self.mentor, title="Règles sans conflit", description="Test", duration_minutes=30,
            price=Decimal("0.00"), published=True, booking_notice_hours=0,
        )
        MentorshipAvailabilityRule.objects.create(
            offering=offer, weekday=2, start_time=time(9, 0), end_time=time(11, 0), interval_minutes=30,
        )
        serializer = MentorshipAvailabilityRuleSerializer(data={
            "offering": offer.id, "weekday": 2, "start_time": "10:30", "end_time": "12:00",
            "interval_minutes": 30, "valid_from": timezone.localdate().isoformat(), "is_active": True,
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn("start_time", serializer.errors)

