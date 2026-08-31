from datetime import timedelta
from urllib.parse import quote
from django.conf import settings
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.http import FileResponse
from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.catalog.permissions import IsInstructorOrAdmin
from .models import (
    InteractiveFormation, FormationSession, FormationEnrollment,
    FormationAttendance, FormationSignal, FormationStatus, FormationRoomFile, FormationSessionInvite,
)
from .serializers import (
    InteractiveFormationListSerializer, InteractiveFormationDetailSerializer,
    InteractiveFormationWriteSerializer, FormationSessionSerializer, FormationSessionWriteSerializer,
    FormationEnrollmentSerializer, AttendanceSerializer,
)

User = get_user_model()


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
    filterset_fields = ["level", "language", "category__slug", "status", "instructor__id"]
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "price", "start_date"]
    lookup_field = "slug"

    def get_queryset(self):
        qs = InteractiveFormation.objects.select_related(
            "instructor", "co_instructor", "category"
        ).prefetch_related("sessions")
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
        instance.delete()

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
        enrollment = FormationEnrollment.objects.filter(user=request.user, formation=session.formation).first()
        if enrollment:
            enrollment.attended_sessions.add(session)
        return Response(AttendanceSerializer(attendance).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
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
            send_mail(
                subject=f"Invitation LearnEas : {session.formation.title}",
                message=(
                    f"Bonjour,\n\n"
                    f"{request.user.get_full_name() or request.user.username} vous invite à participer à la séance "
                    f"{session.session_number} de « {session.formation.title} » sur LearnEas.\n\n"
                    f"Rejoindre la séance : {join_url}\n\n"
                    f"Si vous n'avez pas encore de compte LearnEas, créez-en un avec cette adresse email :\n{register_url}\n\n"
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
            if upload.size > max_size:
                return Response({"file": ["Le fichier dépasse la limite de 20 Mo."]}, status=400)
            blocked = {".exe", ".msi", ".bat", ".cmd", ".com", ".scr", ".js", ".vbs", ".ps1", ".sh"}
            lower_name = upload.name.lower()
            if any(lower_name.endswith(ext) for ext in blocked):
                return Response({"file": ["Ce type de fichier n'est pas autorisé dans une salle live."]}, status=400)
            item = FormationRoomFile.objects.create(
                session=session,
                uploader=request.user,
                file=upload,
                original_name=upload.name[:255],
                content_type=getattr(upload, "content_type", "") or "",
                size=upload.size,
            )
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
        response = FileResponse(handle, as_attachment=True, filename=item.original_name)
        if item.content_type:
            response["Content-Type"] = item.content_type
        response["X-Content-Type-Options"] = "nosniff"
        return response

    @action(detail=True, methods=["get", "post"])
    def signal(self, request, pk=None):
        session = self.get_object()
        self._require_access(request, session)
        if request.method == "POST":
            recipient_id = request.data.get("recipient_id")
            kind = request.data.get("kind")
            payload = request.data.get("payload") or {}
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
                self._require_organizer(request, session)
                action_name = payload.get("action")
                if action_name not in {"mute", "camera_off", "remove"}:
                    return Response({"payload": ["Action de modération invalide."]}, status=400)
                payload = {"action": action_name}
            if kind == FormationSignal.Kind.CODE:
                text = str(payload.get("text", ""))
                if len(text) > 100000:
                    return Response({"payload": ["Le code partagé est limité à 100 000 caractères."]}, status=400)
                language = str(payload.get("language", "text"))
                if language not in {"javascript", "html", "css", "python", "java", "c", "cpp", "text"}:
                    return Response({"payload": ["Langage de code invalide."]}, status=400)
                file_name = str(payload.get("file_name", "code.txt")).strip()[:80] or "code.txt"
                payload = {
                    "text": text,
                    "language": language,
                    "file_name": file_name,
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
            return Response({"id": signal.id}, status=201)

        after = request.query_params.get("after", "0")
        try:
            after_id = int(after)
        except ValueError:
            after_id = 0
        signals = FormationSignal.objects.filter(
            session=session, recipient=request.user, id__gt=after_id
        ).select_related("sender")[:100]
        return Response([
            {
                "id": s.id,
                "sender_id": s.sender_id,
                "sender_name": s.sender.get_full_name() or s.sender.username,
                "kind": s.kind,
                "payload": s.payload,
            }
            for s in signals
        ])

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
