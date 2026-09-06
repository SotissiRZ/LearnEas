import json
from pathlib import Path
from datetime import timedelta, timezone as dt_timezone
from urllib.parse import quote
from django.conf import settings
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.http import FileResponse, HttpResponse
from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.utils import timezone
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.catalog.permissions import IsInstructorOrAdmin
from apps.accounts.serializers import UserPublicCompactSerializer
from apps.common.throttles import LiveRateThrottle
from apps.common.media_metadata import validate_upload_limits
from .models import (
    InteractiveFormation, FormationSession, FormationEnrollment,
    FormationAttendance, FormationSignal, FormationStatus, FormationRoomFile, FormationSessionInvite,
    FormationKind, FormationWaitlistEntry, MentorshipOffering, MentorshipSlot, MentorshipBooking,
    MentorshipPack, MentorshipPass, MentorshipAvailabilityRule,
)
from .rtc import ice_servers_for_user
from .realtime import (
    make_realtime_ticket, publish_files_changed, publish_presence_changed,
    publish_session_state, publish_signal, serialize_signal,
)
from .serializers import (
    InteractiveFormationListSerializer, InteractiveFormationDetailSerializer,
    InteractiveFormationWriteSerializer, FormationSessionSerializer, FormationSessionWriteSerializer,
    FormationEnrollmentSerializer, AttendanceSerializer,
    MentorshipOfferingListSerializer, MentorshipOfferingWriteSerializer,
    MentorshipSlotSerializer, MentorshipBookingSerializer, MentorshipPackSerializer,
    MentorshipPassSerializer, MentorshipAvailabilityRuleSerializer,
)

User = get_user_model()

ROOM_FILE_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".txt", ".csv", ".md", ".json",
    ".png", ".jpg", ".jpeg", ".webp", ".gif",
}


def _enrolled_formation_ids(user):
    if not user or not user.is_authenticated:
        return set()
    return set(FormationEnrollment.objects.filter(user=user).values_list("formation_id", flat=True))


def _is_organizer(user, formation):
    return bool(user.is_authenticated and (
        user.role == "admin" or formation.instructor_id == user.id or formation.co_instructor_id == user.id
    ))


def _active_session_invite(user, session):
    if not user or not user.is_authenticated or not user.email:
        return None
    return FormationSessionInvite.objects.filter(
        session=session, email__iexact=user.email, revoked_at__isnull=True
    ).first()


def _can_access_session(user, session):
    if _is_organizer(user, session.formation):
        return True
    if FormationEnrollment.objects.filter(user=user, formation=session.formation).exists():
        return True
    return _active_session_invite(user, session) is not None


def _role_for(user, formation, session=None):
    if user.role == "admin" and user.id not in (formation.instructor_id, formation.co_instructor_id):
        return FormationAttendance.Role.ADMIN
    if user.id in (formation.instructor_id, formation.co_instructor_id):
        return FormationAttendance.Role.ORGANIZER
    if session is not None and _active_session_invite(user, session):
        return FormationAttendance.Role.GUEST
    return FormationAttendance.Role.PARTICIPANT


def _close_stale_attendances(session, max_idle_seconds=45):
    """Clôture les présences abandonnées sans gonfler artificiellement leur durée."""
    cutoff = timezone.now() - timedelta(seconds=max_idle_seconds)
    stale = FormationAttendance.objects.filter(
        session=session, left_at__isnull=True, last_seen_at__lt=cutoff
    )
    for attendance in stale.iterator():
        when = attendance.last_seen_at or attendance.joined_at
        attendance.left_at = when
        attendance.duration_seconds = max(int((when - attendance.joined_at).total_seconds()), 0)
        attendance.save(update_fields=["left_at", "duration_seconds"])


class InteractiveFormationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsInstructorOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        "level", "language", "category__slug", "category__domain__slug", "status", "instructor__id"
    ]
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "price", "start_date"]
    lookup_field = "slug"

    def get_queryset(self):
        qs = InteractiveFormation.objects.select_related(
            "instructor", "co_instructor", "category", "category__domain"
        ).annotate(
            _students_count=Count("enrollments", filter=Q(enrollments__revoked_at__isnull=True), distinct=True),
            _waitlist_count=Count(
                "waitlist_entries", filter=Q(waitlist_entries__status=FormationWaitlistEntry.Status.WAITING), distinct=True
            ),
            _waitlist_offered_count=Count(
                "waitlist_entries",
                filter=Q(
                    waitlist_entries__status=FormationWaitlistEntry.Status.OFFERED,
                    waitlist_entries__offer_expires_at__gt=timezone.now(),
                ),
                distinct=True,
            ),
        ).filter(kind=FormationKind.COHORT)
        if self.action in ("retrieve", "my_formations"):
            qs = qs.prefetch_related("sessions")
        user = self.request.user
        if self.action == "my_formations" and user.is_authenticated:
            return qs.filter(Q(instructor=user) | Q(co_instructor=user)).distinct()
        if user.is_authenticated and user.role == "admin":
            return qs
        if user.is_authenticated and user.role == "instructor":
            return qs.filter(Q(published=True) | Q(instructor=user) | Q(co_instructor=user)).distinct()
        return qs.filter(published=True)

    def get_serializer_class(self):
        if self.action == "list":
            return InteractiveFormationListSerializer
        if self.action in ("create", "update", "partial_update"):
            return InteractiveFormationWriteSerializer
        return InteractiveFormationDetailSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["enrolled_formation_ids"] = _enrolled_formation_ids(self.request.user)
        return ctx

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def my_formations(self, request):
        qs = self.get_queryset()
        serializer = InteractiveFormationDetailSerializer(qs, many=True, context=self.get_serializer_context())
        return Response(serializer.data)

    @action(detail=True, methods=["get"], permission_classes=[permissions.IsAuthenticated], url_path="waitlist")
    def waitlist(self, request, slug=None):
        formation = self.get_object()
        if not _is_organizer(request.user, formation):
            return Response({"detail": "Action réservée aux responsables de cette cohorte."}, status=403)
        # Met à jour les offres expirées avant d'afficher la file opérationnelle.
        from .cohorts import refresh_waitlist
        refresh_waitlist(formation.id)
        entries = list(
            FormationWaitlistEntry.objects.filter(formation=formation)
            .select_related("user")
            .exclude(status=FormationWaitlistEntry.Status.CANCELLED)
            .order_by("created_at", "id")
        )
        waiting_position = 0
        rows = []
        for entry in entries:
            position = None
            if entry.status == FormationWaitlistEntry.Status.WAITING:
                waiting_position += 1
                position = waiting_position
            rows.append({
                "id": entry.id,
                "status": entry.status,
                "position": position,
                "user": UserPublicCompactSerializer(entry.user, context={"request": request}).data,
                "offered_at": entry.offered_at,
                "offer_expires_at": entry.offer_expires_at,
                "joined_at": entry.joined_at,
                "created_at": entry.created_at,
            })
        return Response({
            "waiting": sum(1 for row in rows if row["status"] == FormationWaitlistEntry.Status.WAITING),
            "offered": sum(1 for row in rows if row["status"] == FormationWaitlistEntry.Status.OFFERED),
            "results": rows,
        })

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def join_waitlist(self, request, slug=None):
        formation = self.get_object()
        try:
            from .cohorts import join_waitlist
            entry = join_waitlist(request.user, formation)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=409)
        from .cohorts import waitlist_snapshot
        return Response(waitlist_snapshot(request.user, formation), status=201)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def leave_waitlist(self, request, slug=None):
        formation = self.get_object()
        from .cohorts import leave_waitlist, waitlist_snapshot
        leave_waitlist(request.user, formation)
        return Response(waitlist_snapshot(request.user, formation))

    @action(detail=True, methods=["get"])
    def calendar(self, request, slug=None):
        formation = self.get_object()
        def esc(value):
            return str(value or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
        lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//KalanPro//Cohorte//FR", "CALSCALE:GREGORIAN"]
        for session in formation.sessions.all():
            start = session.scheduled_at.astimezone(dt_timezone.utc)
            end = start + timedelta(minutes=session.duration_minutes)
            lines.extend([
                "BEGIN:VEVENT",
                f"UID:kalanpro-formation-{formation.id}-session-{session.id}@kalanpro",
                f"DTSTAMP:{timezone.now().astimezone(dt_timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
                f"DTSTART:{start.strftime('%Y%m%dT%H%M%SZ')}",
                f"DTEND:{end.strftime('%Y%m%dT%H%M%SZ')}",
                f"SUMMARY:{esc(formation.title)} · Séance {session.session_number}",
                f"DESCRIPTION:{esc('Séance live KalanPro')}",
                "END:VEVENT",
            ])
        lines.append("END:VCALENDAR")
        response = HttpResponse("\r\n".join(lines) + "\r\n", content_type="text/calendar; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="kalanpro-{formation.slug}.ics"'
        return response


class FormationSessionViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["formation", "completed"]
    search_fields = ["formation__title", "formation__instructor__email", "formation__instructor__first_name", "formation__instructor__last_name"]
    ordering_fields = ["scheduled_at", "session_number", "started_at", "ended_at"]
    ordering = ["-scheduled_at"]

    def get_queryset(self):
        qs = FormationSession.objects.select_related(
            "formation__instructor", "formation__co_instructor"
        )
        user = self.request.user
        if user.role == "admin":
            return qs
        enrolled_ids = FormationEnrollment.objects.filter(user=user).values_list("formation_id", flat=True)
        invited_session_ids = FormationSessionInvite.objects.filter(
            email__iexact=user.email, revoked_at__isnull=True
        ).values_list("session_id", flat=True) if user.email else []
        return qs.filter(
            Q(formation__instructor=user) | Q(formation__co_instructor=user) |
            Q(formation_id__in=enrolled_ids) | Q(id__in=invited_session_ids)
        ).distinct()

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated], url_path="mine")
    def mine(self, request):
        if request.user.role not in ("instructor", "admin"):
            return Response({"detail": "Compte instructeur requis."}, status=403)
        qs = FormationSession.objects.select_related(
            "formation__instructor", "formation__co_instructor"
        ).filter(Q(formation__instructor=request.user) | Q(formation__co_instructor=request.user)).distinct()
        qs = self.filter_queryset(qs)
        page = self.paginate_queryset(qs)
        serializer = FormationSessionSerializer(page if page is not None else qs, many=True, context=self.get_serializer_context())
        return self.get_paginated_response(serializer.data) if page is not None else Response(serializer.data)

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return FormationSessionWriteSerializer
        return FormationSessionSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["enrolled_formation_ids"] = _enrolled_formation_ids(self.request.user)
        return ctx

    def perform_update(self, serializer):
        if not _is_organizer(self.request.user, self.get_object().formation):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Seul l'organisateur peut modifier cette séance.")
        serializer.save()

    def perform_destroy(self, instance):
        if not _is_organizer(self.request.user, instance.formation):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Seul l'organisateur peut supprimer cette séance.")
        formation = instance.formation
        instance.delete()
        formation.sync_schedule_dates()

    def _require_access(self, request, session):
        if not _can_access_session(request.user, session):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Vous n'avez pas accès à cette séance.")

    def _require_organizer(self, request, session):
        if not _is_organizer(request.user, session.formation):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Action réservée à l'organisateur ou à l'administrateur.")

    @action(detail=True, methods=["get"])
    def room(self, request, pk=None):
        session = self.get_object()
        self._require_access(request, session)
        return Response({
            "id": session.id,
            "room_key": str(session.room_key),
            "title": session.formation.title,
            "session_number": session.session_number,
            "scheduled_at": session.scheduled_at,
            "planned_duration_minutes": session.duration_minutes,
            "started_at": session.started_at,
            "ended_at": session.ended_at,
            "completed": session.completed,
            "is_organizer": _is_organizer(request.user, session.formation),
            "is_guest": bool(_active_session_invite(request.user, session)) and not FormationEnrollment.objects.filter(user=request.user, formation=session.formation).exists(),
            "organizer": {
                "id": session.formation.instructor.id,
                "name": session.formation.instructor.get_full_name() or session.formation.instructor.username,
                "avatar": session.formation.instructor.avatar.url if getattr(session.formation.instructor, "avatar", None) else None,
            },
            "user": {
                "id": request.user.id,
                "name": request.user.get_full_name() or request.user.username,
                "avatar": request.user.avatar.url if getattr(request.user, "avatar", None) else None,
            },
            "ice_servers": ice_servers_for_user(request.user),
        })

    @action(detail=True, methods=["post"], url_path="realtime-ticket")
    def realtime_ticket(self, request, pk=None):
        session = self.get_object()
        self._require_access(request, session)
        if session.completed or session.ended_at:
            return Response({"detail": "Cette séance est terminée."}, status=409)
        return Response({
            "ticket": make_realtime_ticket(session_id=session.id, user_id=request.user.id),
            "expires_in": settings.REALTIME_TICKET_MAX_AGE_SECONDS,
        })

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        session = self.get_object()
        self._require_organizer(request, session)
        if session.ended_at:
            return Response({"detail": "Cette séance est déjà terminée."}, status=400)
        if not session.started_at:
            session.started_at = timezone.now()
            session.formation.status = FormationStatus.IN_PROGRESS
            session.formation.save(update_fields=["status"])
            session.save(update_fields=["started_at"])
            publish_session_state(session.id, "started")
        return Response(FormationSessionSerializer(session, context=self.get_serializer_context()).data)

    @action(detail=True, methods=["post"])
    def join(self, request, pk=None):
        session = self.get_object()
        self._require_access(request, session)
        if session.completed or session.ended_at:
            return Response({"detail": "Cette séance est terminée."}, status=400)
        if not session.started_at and not _is_organizer(request.user, session.formation):
            return Response({"detail": "La séance n'a pas encore été démarrée par l'organisateur."}, status=409)

        # Nettoie les anciens messages WebRTC destinés à une connexion précédente.
        FormationSignal.objects.filter(session=session, recipient=request.user).delete()

        # Ferme une ancienne connexion restée ouverte pour ce même utilisateur/session.
        for old in FormationAttendance.objects.filter(session=session, user=request.user, left_at__isnull=True):
            # Ne jamais compter une période hors-ligne comme du temps de présence. Une ancienne
            # connexion est clôturée à son dernier heartbeat connu, pas à l'instant du nouveau join.
            old.close(old.last_seen_at or timezone.now())

        invite = _active_session_invite(request.user, session)
        if invite:
            update_fields = []
            if invite.invited_user_id != request.user.id:
                invite.invited_user = request.user
                update_fields.append("invited_user")
            if not invite.accepted_at:
                invite.accepted_at = timezone.now()
                update_fields.append("accepted_at")
            if update_fields:
                invite.save(update_fields=update_fields)

        attendance = FormationAttendance.objects.create(
            session=session, user=request.user, role=_role_for(request.user, session.formation, session)
        )
        publish_presence_changed(session.id)
        enrollment = FormationEnrollment.objects.filter(user=request.user, formation=session.formation).first()
        if enrollment:
            enrollment.attended_sessions.add(session)
        return Response(AttendanceSerializer(attendance).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], throttle_classes=[LiveRateThrottle])
    def heartbeat(self, request, pk=None):
        session = self.get_object()
        self._require_access(request, session)
        attendance_id = request.data.get("attendance_id")
        attendance = FormationAttendance.objects.filter(
            id=attendance_id, session=session, user=request.user, left_at__isnull=True
        ).first()
        if not attendance:
            return Response({"detail": "Présence introuvable ou déjà clôturée."}, status=404)
        now = timezone.now()
        attendance.last_seen_at = now
        attendance.duration_seconds = max(int((now - attendance.joined_at).total_seconds()), 0)
        attendance.save(update_fields=["last_seen_at", "duration_seconds"])
        return Response({"ok": True, "duration_seconds": attendance.duration_seconds})

    @action(detail=True, methods=["post"])
    def leave(self, request, pk=None):
        session = self.get_object()
        attendance_id = request.data.get("attendance_id")
        attendance = FormationAttendance.objects.filter(id=attendance_id, session=session, user=request.user).first()
        if attendance and not attendance.left_at:
            attendance.close()
        FormationSignal.objects.filter(session=session).filter(
            Q(sender=request.user) | Q(recipient=request.user)
        ).delete()
        publish_presence_changed(session.id)
        return Response({"ok": True})

    @action(detail=True, methods=["get"])
    def presence(self, request, pk=None):
        session = self.get_object()
        self._require_access(request, session)
        _close_stale_attendances(session)
        cutoff = timezone.now() - timedelta(seconds=45)
        records = FormationAttendance.objects.filter(
            session=session, left_at__isnull=True, last_seen_at__gte=cutoff
        ).select_related("user").order_by("user_id", "-joined_at")
        seen = set()
        people = []
        for record in records:
            if record.user_id in seen:
                continue
            seen.add(record.user_id)
            people.append({
                "user_id": record.user_id,
                "name": record.user.get_full_name() or record.user.username,
                "role": record.role,
                "hand_raised": record.hand_raised,
                "avatar": record.user.avatar.url if getattr(record.user, "avatar", None) else None,
            })
        return Response(people)

    @action(detail=True, methods=["post"])
    def hand(self, request, pk=None):
        session = self.get_object()
        self._require_access(request, session)
        attendance_id = request.data.get("attendance_id")
        attendance = FormationAttendance.objects.filter(
            id=attendance_id, session=session, user=request.user, left_at__isnull=True
        ).first()
        if not attendance:
            return Response({"detail": "Présence introuvable ou déjà clôturée."}, status=404)
        attendance.hand_raised = bool(request.data.get("raised", False))
        attendance.save(update_fields=["hand_raised"])
        publish_presence_changed(session.id)
        return Response({"ok": True, "hand_raised": attendance.hand_raised})

    @action(detail=True, methods=["get", "post"], url_path="invites")
    def invites(self, request, pk=None):
        session = self.get_object()
        self._require_organizer(request, session)

        if request.method == "POST":
            email = str(request.data.get("email", "")).strip().lower()
            if not email:
                return Response({"email": ["Saisissez une adresse email."]}, status=400)
            try:
                validate_email(email)
            except ValidationError:
                return Response({"email": ["Adresse email invalide."]}, status=400)

            if email in {session.formation.instructor.email.lower(), (session.formation.co_instructor.email.lower() if session.formation.co_instructor and session.formation.co_instructor.email else "")}:
                return Response({"email": ["Cette personne organise déjà la séance."]}, status=400)
            existing_user = User.objects.filter(email__iexact=email).first()
            if existing_user and FormationEnrollment.objects.filter(user=existing_user, formation=session.formation).exists():
                return Response({"email": ["Cet apprenant est déjà inscrit à la formation."]}, status=400)

            invite, _ = FormationSessionInvite.objects.update_or_create(
                session=session, email=email,
                defaults={
                    "invited_by": request.user,
                    "invited_user": existing_user,
                    "accepted_at": None,
                    "revoked_at": None,
                },
            )
            join_url = f"{settings.FRONTEND_URL.rstrip('/')}/live/session/{session.id}"
            register_url = f"{settings.FRONTEND_URL.rstrip('/')}/register?next=/live/session/{session.id}&email={quote(email)}"
            try:
                from apps.notifications.email_services import queue_session_invite_email
                delivery = queue_session_invite_email(
                    inviter=request.user, recipient=email, session=session,
                    join_url=join_url, register_url=register_url,
                )
            except Exception:
                delivery = None
            if delivery is None:
                send_mail(
                    subject=f"Invitation KalanPro : {session.formation.title}",
                    message=(
                        f"Bonjour,\n\n"
                        f"{request.user.get_full_name() or request.user.username} vous invite à participer à la séance "
                        f"{session.session_number} de « {session.formation.title} » sur KalanPro.\n\n"
                        f"Rejoindre la séance : {join_url}\n\n"
                        f"Si vous n'avez pas encore de compte KalanPro, créez-en un avec cette adresse email :\n{register_url}\n\n"
                        f"Cette invitation donne accès uniquement à cette séance et ne vous inscrit pas à la formation."
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=True,
                )
            payload = self._invite_payload(invite)
            if settings.DEBUG:
                payload["dev_join_url"] = join_url
            return Response(payload, status=status.HTTP_201_CREATED)

        rows = session.email_invites.select_related("invited_user", "invited_by").all()[:100]
        return Response([self._invite_payload(invite) for invite in rows])

    def _invite_payload(self, invite):
        if invite.revoked_at:
            invite_status = "revoked"
        elif invite.accepted_at:
            invite_status = "accepted"
        elif invite.invited_user_id:
            invite_status = "account_exists"
        else:
            invite_status = "pending_account"
        return {
            "id": invite.id,
            "email": invite.email,
            "status": invite_status,
            "created_at": invite.created_at,
            "accepted_at": invite.accepted_at,
            "user_id": invite.invited_user_id,
        }

    @action(detail=True, methods=["post"], url_path=r"invites/(?P<invite_id>\d+)/revoke")
    def invite_revoke(self, request, pk=None, invite_id=None):
        session = self.get_object()
        self._require_organizer(request, session)
        invite = FormationSessionInvite.objects.filter(id=invite_id, session=session).first()
        if not invite:
            return Response({"detail": "Invitation introuvable."}, status=404)
        invite.revoked_at = timezone.now()
        invite.save(update_fields=["revoked_at"])
        return Response(self._invite_payload(invite))

    @action(detail=True, methods=["get", "post"], url_path="files")
    def files(self, request, pk=None):
        session = self.get_object()
        self._require_access(request, session)
        if request.method == "POST":
            upload = request.FILES.get("file")
            if not upload:
                return Response({"file": ["Sélectionnez un fichier."]}, status=400)
            max_size = 20 * 1024 * 1024
            try:
                validate_upload_limits(
                    upload, max_bytes=max_size, extensions=ROOM_FILE_EXTENSIONS, field="file"
                )
            except Exception as exc:
                detail = getattr(exc, "detail", None)
                if detail is not None:
                    return Response(detail, status=400)
                return Response({"file": ["Fichier invalide ou non autorisé."]}, status=400)
            safe_name = Path(str(getattr(upload, "name", "fichier"))).name[:255] or "fichier"
            item = FormationRoomFile.objects.create(
                session=session,
                uploader=request.user,
                file=upload,
                original_name=safe_name,
                # Le MIME client est conservé uniquement comme métadonnée d'affichage.
                # Le téléchargement, lui, est forcé en octet-stream.
                content_type=(getattr(upload, "content_type", "") or "")[:120],
                size=upload.size,
            )
            publish_files_changed(session.id)
            return Response(self._room_file_payload(item), status=status.HTTP_201_CREATED)

        files = session.room_files.select_related("uploader").all()[:100]
        return Response([self._room_file_payload(item) for item in files])

    def _room_file_payload(self, item):
        return {
            "id": item.id,
            "name": item.original_name,
            "content_type": item.content_type,
            "size": item.size,
            "uploaded_at": item.uploaded_at,
            "uploader_id": item.uploader_id,
            "uploader_name": item.uploader.get_full_name() or item.uploader.username,
            "download_path": f"/sessions/{item.session_id}/files/{item.id}/download/",
        }

    @action(detail=True, methods=["get"], url_path=r"files/(?P<file_id>\d+)/download")
    def file_download(self, request, pk=None, file_id=None):
        session = self.get_object()
        self._require_access(request, session)
        item = FormationRoomFile.objects.filter(id=file_id, session=session).first()
        if not item:
            return Response({"detail": "Fichier introuvable."}, status=404)
        try:
            handle = item.file.open("rb")
        except (FileNotFoundError, OSError):
            return Response({"detail": "Fichier indisponible sur le stockage."}, status=404)
        response = FileResponse(
            handle, as_attachment=True, filename=item.original_name, content_type="application/octet-stream"
        )
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "private, no-store"
        response["Content-Security-Policy"] = "sandbox"
        return response

    @action(detail=True, methods=["get", "post"], throttle_classes=[LiveRateThrottle])
    def signal(self, request, pk=None):
        session = self.get_object()
        self._require_access(request, session)
        if request.method == "POST":
            if session.completed or session.ended_at:
                return Response({"detail": "Cette séance est terminée."}, status=409)
            recipient_id = request.data.get("recipient_id")
            kind = request.data.get("kind")
            payload = request.data.get("payload") or {}
            try:
                if len(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")) > 256_000:
                    return Response({"payload": ["Payload de signalisation trop volumineux."]}, status=413)
            except (TypeError, ValueError):
                return Response({"payload": ["Payload JSON invalide."]}, status=400)
            if kind not in FormationSignal.Kind.values:
                return Response({"kind": ["Type de signal invalide."]}, status=400)
            if kind == FormationSignal.Kind.CHAT:
                text = str(payload.get("text", "")).strip()
                if not text:
                    return Response({"payload": ["Le message ne peut pas être vide."]}, status=400)
                if len(text) > 2000:
                    return Response({"payload": ["Le message est limité à 2000 caractères."]}, status=400)
                payload = {"text": text, "sent_at": payload.get("sent_at")}
            if kind == FormationSignal.Kind.CONTROL:
                action_name = str(payload.get("action") or "")
                if action_name == "screen_share_state":
                    # Etat d'interface collaboratif : chaque participant autorisé
                    # peut annoncer le début/la fin de SON partage. Aucun droit de
                    # modération n'est accordé par cette action.
                    payload = {
                        "action": "screen_share_state",
                        "active": bool(payload.get("active")),
                        "sent_at": payload.get("sent_at"),
                    }
                else:
                    self._require_organizer(request, session)
                    if action_name not in {"mute", "camera_off", "remove"}:
                        return Response({"payload": ["Action de modération invalide."]}, status=400)
                    payload = {"action": action_name}
            if kind == FormationSignal.Kind.CODE:
                allowed_languages = {"javascript", "html", "css", "python", "java", "c", "cpp", "text"}
                allowed_frameworks = {"none", "react", "nextjs", "django", "drf", "fastapi", "flask", "express"}
                text = str(payload.get("text", ""))
                if len(text) > 100000:
                    return Response({"payload": ["Le code partagé est limité à 100 000 caractères par fichier."]}, status=400)
                language = str(payload.get("language", "text"))
                if language not in allowed_languages:
                    return Response({"payload": ["Langage de code invalide."]}, status=400)
                file_name = str(payload.get("file_name", "code.txt")).strip()[:120] or "code.txt"
                framework = str(payload.get("framework", "none"))
                if framework not in allowed_frameworks:
                    return Response({"payload": ["Framework invalide."]}, status=400)
                raw_files = payload.get("files", [])
                cleaned_files = []
                seen_paths = set()
                total_chars = 0
                if raw_files:
                    if not isinstance(raw_files, list) or len(raw_files) > 30:
                        return Response({"payload": ["Un projet est limité à 30 fichiers."]}, status=400)
                    for item in raw_files:
                        if not isinstance(item, dict):
                            return Response({"payload": ["Structure de fichier invalide."]}, status=400)
                        path = str(item.get("path", "")).strip().replace("\\", "/")[:160]
                        if not path or path.startswith("/") or ".." in path.split("/"):
                            return Response({"payload": ["Chemin de fichier invalide."]}, status=400)
                        path_key = path.lower()
                        if path_key in seen_paths:
                            return Response({"payload": [f"Chemin de fichier dupliqué : {path}"]}, status=400)
                        seen_paths.add(path_key)
                        file_language = str(item.get("language", "text"))
                        if file_language not in allowed_languages:
                            return Response({"payload": ["Langage de fichier invalide."]}, status=400)
                        content = str(item.get("content", ""))
                        if len(content) > 100000:
                            return Response({"payload": [f"Le fichier {path} dépasse 100 000 caractères."]}, status=400)
                        total_chars += len(content)
                        if total_chars > 220000:
                            return Response({"payload": ["Le projet partagé dépasse 220 000 caractères."]}, status=413)
                        cleaned_files.append({
                            "id": str(item.get("id", path))[:160],
                            "path": path,
                            "language": file_language,
                            "content": content,
                        })
                active_file_id = str(payload.get("active_file_id", ""))[:160]
                payload = {
                    "text": text,
                    "language": language,
                    "file_name": file_name,
                    "framework": framework,
                    "active_file_id": active_file_id,
                    "files": cleaned_files,
                    "sent_at": payload.get("sent_at"),
                }
            if kind == FormationSignal.Kind.WHITEBOARD:
                strokes = payload.get("strokes", [])
                if not isinstance(strokes, list) or len(strokes) > 120:
                    return Response({"payload": ["Le tableau blanc dépasse la limite de 120 tracés."]}, status=400)
                cleaned = []
                total_points = 0
                for stroke in strokes:
                    if not isinstance(stroke, dict):
                        continue
                    points = stroke.get("points", [])
                    if not isinstance(points, list):
                        continue
                    points = points[:600]
                    total_points += len(points)
                    if total_points > 12000:
                        return Response({"payload": ["Le tableau blanc contient trop de points."]}, status=400)
                    cleaned_points = []
                    for point in points:
                        if not isinstance(point, dict):
                            continue
                        try:
                            x = min(max(float(point.get("x", 0)), 0.0), 1.0)
                            y = min(max(float(point.get("y", 0)), 0.0), 1.0)
                        except (TypeError, ValueError):
                            continue
                        cleaned_points.append({"x": round(x, 4), "y": round(y, 4)})
                    color = str(stroke.get("color", "#10b981"))[:16]
                    try:
                        width = min(max(float(stroke.get("width", 3)), 1.0), 16.0)
                    except (TypeError, ValueError):
                        width = 3.0
                    cleaned.append({
                        "id": str(stroke.get("id", ""))[:80],
                        "color": color,
                        "width": width,
                        "points": cleaned_points,
                    })
                payload = {"strokes": cleaned, "sent_at": payload.get("sent_at")}
            try:
                recipient = User.objects.get(id=recipient_id)
            except User.DoesNotExist:
                return Response({"recipient_id": ["Participant introuvable."]}, status=400)
            if not _can_access_session(recipient, session):
                return Response({"recipient_id": ["Ce participant n'a pas accès à la séance."]}, status=400)
            if kind in {FormationSignal.Kind.CODE, FormationSignal.Kind.WHITEBOARD}:
                FormationSignal.objects.filter(
                    session=session, sender=request.user, recipient=recipient, kind=kind
                ).delete()
            signal = FormationSignal.objects.create(
                session=session, sender=request.user, recipient=recipient, kind=kind, payload=payload
            )
            publish_signal(signal)
            return Response({"id": signal.id}, status=201)

        after = request.query_params.get("after", "0")
        try:
            after_id = int(after)
        except ValueError:
            after_id = 0
        signals = FormationSignal.objects.filter(
            session=session, recipient=request.user, id__gt=after_id
        ).select_related("sender")[:100]
        return Response([serialize_signal(signal) for signal in signals])

    @action(detail=True, methods=["post"])
    def end(self, request, pk=None):
        session = self.get_object()
        self._require_organizer(request, session)
        now = timezone.now()
        if not session.started_at:
            session.started_at = now
        session.ended_at = now
        session.actual_duration_seconds = max(int((now - session.started_at).total_seconds()), 0)
        session.completed = True
        session.save(update_fields=["started_at", "ended_at", "actual_duration_seconds", "completed"])

        # Ferme d'abord les connexions déjà inactives à leur dernier heartbeat connu.
        _close_stale_attendances(session)
        for attendance in FormationAttendance.objects.filter(session=session, left_at__isnull=True):
            attendance.close(now)
        session.signals.all().delete()
        publish_presence_changed(session.id)
        publish_session_state(session.id, "ended")

        if not session.formation.sessions.filter(completed=False).exists():
            session.formation.status = FormationStatus.COMPLETED
            session.formation.save(update_fields=["status"])
            if session.formation.certificate_enabled and session.formation.certificate_auto_issue:
                from apps.enrollments.certificates import formation_eligibility, issue_formation_certificate
                for enrollment in session.formation.enrollments.select_related("user").all():
                    if formation_eligibility(enrollment)["eligible"]:
                        issue_formation_certificate(enrollment, issued_by=session.formation.instructor)
        return Response(FormationSessionSerializer(session, context=self.get_serializer_context()).data)

    @action(detail=True, methods=["get"])
    def report(self, request, pk=None):
        session = self.get_object()
        self._require_organizer(request, session)
        _close_stale_attendances(session)

        # Le temps pédagogique est calculé à partir de la fenêtre réelle de la séance.
        # Cela corrige aussi les anciennes présences restées ouvertes plusieurs heures/jours.
        session_start = session.started_at
        session_end = session.ended_at or timezone.now()
        aggregated = {}
        attendances = FormationAttendance.objects.filter(session=session).select_related("user").order_by("joined_at")
        for attendance in attendances:
            user = attendance.user
            key = (user.id, attendance.role)
            row = aggregated.setdefault(key, {
                "user_id": user.id,
                "name": user.get_full_name() or user.username,
                "email": user.email,
                "role": attendance.role,
                "first_join": attendance.joined_at,
                "last_leave": attendance.left_at,
                "total_seconds": 0,
            })
            row["first_join"] = min(row["first_join"], attendance.joined_at)
            if attendance.left_at and (not row["last_leave"] or attendance.left_at > row["last_leave"]):
                row["last_leave"] = attendance.left_at

            if not session_start:
                continue
            started = max(attendance.joined_at, session_start)
            observed_end = attendance.left_at or attendance.last_seen_at or started
            ended = min(observed_end, session_end)
            if ended > started:
                row["total_seconds"] += int((ended - started).total_seconds())

        # Aucun participant ne peut avoir plus de présence que la durée réelle de la séance.
        max_session_seconds = 0
        if session_start:
            max_session_seconds = max(int((session_end - session_start).total_seconds()), 0)
        rows = []
        for row in aggregated.values():
            if max_session_seconds:
                row["total_seconds"] = min(row["total_seconds"], max_session_seconds)
            else:
                row["total_seconds"] = 0
            rows.append(row)
        rows.sort(key=lambda row: row["first_join"])

        organizers = [session.formation.instructor]
        if session.formation.co_instructor:
            organizers.append(session.formation.co_instructor)
        return Response({
            "session": FormationSessionSerializer(session, context=self.get_serializer_context()).data,
            "organizers": [
                {
                    "id": u.id,
                    "name": u.get_full_name() or u.username,
                    "email": u.email,
                    "avatar": u.avatar.url if getattr(u, "avatar", None) else None,
                }
                for u in organizers
            ],
            "participants": rows,
        })



class MyFormationsViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FormationEnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return FormationEnrollment.objects.filter(user=self.request.user).select_related("formation", "formation__instructor", "formation__co_instructor", "formation__category")

class MentorshipOfferingViewSet(viewsets.ModelViewSet):
    permission_classes = [IsInstructorOrAdmin]
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["instructor__id", "language", "published"]
    search_fields = ["title", "description", "instructor__first_name", "instructor__last_name"]
    ordering_fields = ["created_at", "price", "duration_minutes"]
    ordering = ["-created_at"]

    def get_queryset(self):
        mentorship_slots = MentorshipSlot.objects.select_related("offering").prefetch_related(
            "bookings__order_items__order"
        )
        qs = MentorshipOffering.objects.select_related("instructor", "room_formation").prefetch_related(
            Prefetch("slots", queryset=mentorship_slots), "packs", "availability_rules"
        )
        user = self.request.user
        if self.action == "mine" and user.is_authenticated:
            return qs.filter(instructor=user)
        if user.is_authenticated and user.role == "admin":
            return qs
        if user.is_authenticated and user.role == "instructor":
            return qs.filter(Q(published=True) | Q(instructor=user)).distinct()
        return qs.filter(published=True)

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return MentorshipOfferingWriteSerializer
        return MentorshipOfferingListSerializer

    def perform_create(self, serializer):
        offering = serializer.save(instructor=self.request.user)
        from .mentorship import ensure_room_formation
        ensure_room_formation(offering)

    def perform_update(self, serializer):
        offering = serializer.save()
        if offering.room_formation_id:
            room = offering.room_formation
            room.title = f"Mentorat privé · {offering.title}"
            room.language = offering.language
            room.session_duration_minutes = offering.duration_minutes
            room.cohort_timezone = offering.timezone
            room.save(update_fields=["title", "language", "session_duration_minutes", "cohort_timezone"])

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        offering = self.get_object()
        if offering.bookings.exists():
            return Response({
                "detail": "Cette offre possède déjà un historique de réservation. Dépubliez-la au lieu de la supprimer."
            }, status=409)
        room_id = offering.room_formation_id
        offering.delete()
        if room_id:
            # Sans réservation, le conteneur et ses séances ne portent aucun historique métier.
            InteractiveFormation.objects.filter(pk=room_id, kind=FormationKind.MENTORSHIP).delete()
        return Response(status=204)

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def mine(self, request):
        if request.user.role not in ("instructor", "admin"):
            return Response({"detail": "Compte instructeur requis."}, status=403)
        return Response(MentorshipOfferingListSerializer(
            self.get_queryset(), many=True, context=self.get_serializer_context()
        ).data)


class MentorshipSlotViewSet(viewsets.ModelViewSet):
    serializer_class = MentorshipSlotSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["offering", "is_active"]
    ordering_fields = ["starts_at"]
    ordering = ["starts_at"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        from .mentorship import expire_stale_bookings
        expire_stale_bookings()
        qs = MentorshipSlot.objects.select_related("offering", "offering__instructor", "session").prefetch_related("bookings")
        if self.request.user.is_authenticated and self.request.user.role == "admin":
            return qs
        if self.request.user.is_authenticated and self.request.user.role == "instructor":
            return qs.filter(Q(offering__published=True) | Q(offering__instructor=self.request.user)).distinct()
        return qs.filter(offering__published=True, is_active=True, starts_at__gt=timezone.now())

    def create(self, request, *args, **kwargs):
        if request.user.role not in ("instructor", "admin"):
            return Response({"detail": "Compte instructeur requis."}, status=403)
        offering = MentorshipOffering.objects.filter(pk=request.data.get("offering")).first()
        if not offering:
            return Response({"offering": ["Offre introuvable."]}, status=404)
        if request.user.role != "admin" and offering.instructor_id != request.user.id:
            return Response({"detail": "Vous ne pouvez gérer que vos propres créneaux."}, status=403)
        raw = request.data.get("starts_at")
        try:
            from django.utils.dateparse import parse_datetime
            starts_at = parse_datetime(str(raw))
            if starts_at is None:
                raise ValueError
            if timezone.is_naive(starts_at):
                starts_at = timezone.make_aware(starts_at)
        except Exception:
            return Response({"starts_at": ["Date et heure invalides."]}, status=400)
        if starts_at <= timezone.now():
            return Response({"starts_at": ["Le créneau doit être dans le futur."]}, status=400)
        try:
            from .mentorship import create_slot
            slot = create_slot(offering, starts_at, bool(request.data.get("is_active", True)))
        except Exception as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(self.get_serializer(slot).data, status=201)

    def partial_update(self, request, *args, **kwargs):
        slot = self.get_object()
        if request.user.role != "admin" and slot.offering.instructor_id != request.user.id:
            return Response({"detail": "Action interdite."}, status=403)
        extra = set(request.data.keys()) - {"is_active"}
        if extra:
            return Response({"detail": "Seule l'activation du créneau peut être modifiée. Créez un nouveau créneau pour changer l'horaire."}, status=400)
        if "is_active" not in request.data:
            return Response({"is_active": ["Valeur requise."]}, status=400)
        raw = request.data.get("is_active")
        if isinstance(raw, str):
            is_active = raw.strip().lower() in {"1", "true", "yes", "oui"}
        else:
            is_active = bool(raw)
        slot.is_active = is_active
        slot.save(update_fields=["is_active"])
        return Response(self.get_serializer(slot).data)

    def destroy(self, request, *args, **kwargs):
        slot = self.get_object()
        if request.user.role != "admin" and slot.offering.instructor_id != request.user.id:
            return Response({"detail": "Action interdite."}, status=403)
        from .mentorship import expire_stale_bookings
        expire_stale_bookings(slot)
        if slot.bookings.exists():
            return Response({
                "detail": "Ce créneau possède un historique de réservation. Désactivez-le au lieu de le supprimer."
            }, status=409)
        session = slot.session
        slot.delete()
        if session:
            session.delete()
        return Response(status=204)


class MentorshipBookingViewSet(viewsets.ModelViewSet):
    serializer_class = MentorshipBookingSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status", "offering"]
    ordering_fields = ["created_at", "slot__starts_at"]
    ordering = ["-created_at"]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        from .mentorship import expire_stale_bookings
        expire_stale_bookings()
        qs = MentorshipBooking.objects.select_related(
            "user", "offering", "offering__instructor", "slot", "slot__session"
        )
        if self.request.user.role == "admin":
            return qs
        if self.request.user.role == "instructor":
            if self.action in {"retrieve", "cancel", "complete", "reschedule"}:
                return qs.filter(Q(user=self.request.user) | Q(offering__instructor=self.request.user)).distinct()
            if self.request.query_params.get("as_mentor") == "1":
                return qs.filter(offering__instructor=self.request.user)
        return qs.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        slot = MentorshipSlot.objects.select_related("offering").filter(pk=request.data.get("slot_id")).first()
        if not slot:
            return Response({"slot_id": ["Créneau introuvable."]}, status=404)
        if slot.offering.instructor_id == request.user.id:
            return Response({"detail": "Un mentor ne peut pas réserver son propre créneau."}, status=400)
        try:
            from .mentorship import reserve_booking
            booking = reserve_booking(
                user=request.user,
                slot=slot,
                learner_note=request.data.get("learner_note", ""),
                mentorship_pass=request.data.get("pass_id") or None,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=409)
        data = self.get_serializer(booking).data
        return Response(data, status=201)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def cancel(self, request, pk=None):
        visible = self.get_object()
        # slot.session est nullable : l'inclure dans select_related() avec FOR UPDATE
        # provoque une erreur PostgreSQL (verrou sur le côté nullable d'un OUTER JOIN).
        booking = MentorshipBooking.objects.select_for_update().select_related(
            "user", "offering", "slot"
        ).get(pk=visible.pk)
        can_manage = request.user.role == "admin" or booking.user_id == request.user.id or booking.offering.instructor_id == request.user.id
        if not can_manage:
            return Response({"detail": "Action interdite."}, status=403)
        if booking.status not in (MentorshipBooking.Status.PENDING_PAYMENT, MentorshipBooking.Status.CONFIRMED):
            return Response({"detail": "Cette réservation ne peut plus être annulée."}, status=409)

        if booking.status == MentorshipBooking.Status.PENDING_PAYMENT:
            # Une commande externe peut être confirmée quelques secondes/minutes après le clic.
            # Tant que cette commande est PENDING, libérer le créneau créerait un risque de
            # double réservation après le webhook Mobile Money/carte.
            if booking.order_items.filter(order__status="pending").exists():
                return Response({
                    "detail": "Un paiement est déjà en cours pour ce rendez-vous. Attendez sa confirmation ou son échec avant d'annuler."
                }, status=409)
            if booking.order_items.filter(order__status="paid").exists():
                return Response({
                    "detail": "Le paiement de ce rendez-vous est déjà confirmé. Actualisez la page avant toute annulation."
                }, status=409)

        if (
            booking.status == MentorshipBooking.Status.CONFIRMED
            and booking.user_id == request.user.id
            and request.user.role != "admin"
            and booking.slot.starts_at <= timezone.now() + timedelta(hours=booking.offering.cancellation_notice_hours)
        ):
            return Response({
                "detail": f"L'annulation par l'apprenant doit intervenir au moins {booking.offering.cancellation_notice_hours} h avant le rendez-vous."
            }, status=409)

        # Les remboursements restent volontairement séparés : annuler un rendez-vous payé ne
        # déclenche jamais silencieusement un remboursement financier.
        booking.status = MentorshipBooking.Status.CANCELLED
        booking.cancelled_at = timezone.now()
        booking.expires_at = None
        booking.save(update_fields=["status", "cancelled_at", "expires_at", "updated_at"])
        if booking.mentorship_pass_id:
            from .mentorship import restore_pass_credit
            restore_pass_credit(booking)
        if booking.slot.session_id and booking.user.email:
            FormationSessionInvite.objects.filter(
                session_id=booking.slot.session_id, email__iexact=booking.user.email, revoked_at__isnull=True
            ).update(revoked_at=timezone.now())
        return Response(self.get_serializer(booking).data)

    @action(detail=True, methods=["post"])
    def reschedule(self, request, pk=None):
        booking = self.get_object()
        if request.user.role != "admin" and booking.user_id != request.user.id and booking.offering.instructor_id != request.user.id:
            return Response({"detail": "Action interdite."}, status=403)
        new_slot = MentorshipSlot.objects.select_related("offering").filter(pk=request.data.get("slot_id")).first()
        if not new_slot:
            return Response({"slot_id": ["Créneau introuvable."]}, status=404)
        try:
            from .mentorship import reschedule_booking
            booking = reschedule_booking(booking=booking, new_slot=new_slot)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=409)
        try:
            from apps.notifications.models import InAppNotification
            from apps.notifications.services import queue_in_app_event
            transaction.on_commit(lambda: queue_in_app_event(
                user=booking.user,
                event_key=f"inapp:mentorship-rescheduled:{booking.id}:{booking.reschedule_count}",
                category=InAppNotification.Category.MENTORSHIP,
                event_type="mentorship_rescheduled",
                title="Rendez-vous reprogrammé",
                body=f"Votre séance {booking.offering.title} a été déplacée.",
                action_url=f"{settings.FRONTEND_URL.rstrip('/')}/dashboard/student/mentorship",
                metadata={"booking_id": booking.id, "slot_id": booking.slot_id},
            ))
        except Exception:
            pass
        return Response(self.get_serializer(booking).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        booking = self.get_object()
        if request.user.role != "admin" and booking.offering.instructor_id != request.user.id:
            return Response({"detail": "Seul le mentor peut clôturer ce rendez-vous."}, status=403)
        if booking.status != MentorshipBooking.Status.CONFIRMED:
            return Response({"detail": "Seule une réservation confirmée peut être clôturée."}, status=409)
        booking.status = MentorshipBooking.Status.COMPLETED
        booking.mentor_note = str(request.data.get("mentor_note", "")).strip()
        booking.save(update_fields=["status", "mentor_note", "updated_at"])
        return Response(self.get_serializer(booking).data)



class MentorshipPackViewSet(viewsets.ModelViewSet):
    serializer_class = MentorshipPackSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["offering", "published"]
    ordering_fields = ["sessions_count", "price"]
    ordering = ["sessions_count"]

    def get_queryset(self):
        qs = MentorshipPack.objects.select_related("offering", "offering__instructor")
        user = self.request.user
        if user.is_authenticated and user.role == "admin":
            return qs
        if user.is_authenticated and user.role == "instructor":
            return qs.filter(Q(published=True) | Q(offering__instructor=user)).distinct()
        return qs.filter(published=True, offering__published=True)

    def perform_create(self, serializer):
        offering = serializer.validated_data["offering"]
        if self.request.user.role != "admin" and offering.instructor_id != self.request.user.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Vous ne pouvez créer des packs que pour vos propres offres.")
        serializer.save()

    def perform_update(self, serializer):
        obj = self.get_object()
        if self.request.user.role != "admin" and obj.offering.instructor_id != self.request.user.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Action interdite.")
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        if request.user.role != "admin" and obj.offering.instructor_id != request.user.id:
            return Response({"detail": "Action interdite."}, status=403)
        if obj.passes.exists() or obj.order_items.exists():
            obj.published = False
            obj.save(update_fields=["published"])
            return Response({"detail": "Pack dépublié car il possède déjà un historique."}, status=200)
        return super().destroy(request, *args, **kwargs)


class MentorshipPassViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MentorshipPassSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["pack__offering"]
    ordering_fields = ["created_at", "expires_at", "remaining_sessions"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = MentorshipPass.objects.select_related("pack", "pack__offering")
        if self.request.user.role == "admin":
            return qs
        return qs.filter(user=self.request.user)


class MentorshipAvailabilityRuleViewSet(viewsets.ModelViewSet):
    serializer_class = MentorshipAvailabilityRuleSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["offering", "weekday", "is_active"]
    ordering = ["weekday", "start_time"]

    def get_queryset(self):
        qs = MentorshipAvailabilityRule.objects.select_related("offering", "offering__instructor")
        if self.request.user.role == "admin":
            return qs
        return qs.filter(offering__instructor=self.request.user)

    def perform_create(self, serializer):
        offering = serializer.validated_data["offering"]
        if self.request.user.role != "admin" and offering.instructor_id != self.request.user.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Action interdite.")
        rule = serializer.save()
        from .mentorship import generate_rule_slots
        generate_rule_slots(rule)

    def perform_update(self, serializer):
        rule = serializer.save()
        from .mentorship import generate_rule_slots
        generate_rule_slots(rule)

    def destroy(self, request, *args, **kwargs):
        rule = self.get_object()
        # Une règle ayant déjà généré des créneaux est conservée comme historique :
        # on la désactive et on retire seulement ses disponibilités futures libres.
        if rule.generated_slots.exists():
            rule.is_active = False
            rule.save(update_fields=["is_active"])
            from .mentorship import generate_rule_slots
            generate_rule_slots(rule)
            return Response({"detail": "Règle désactivée car elle possède déjà un historique."}, status=200)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def generate(self, request, pk=None):
        rule = self.get_object()
        from .mentorship import generate_rule_slots
        try:
            horizon_days = int(request.data.get("horizon_days", 45))
        except (TypeError, ValueError):
            return Response({"horizon_days": ["Valeur entière invalide."]}, status=400)
        created = generate_rule_slots(rule, horizon_days=horizon_days)
        return Response({"created": created})
