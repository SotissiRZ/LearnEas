from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db.models import Q, Sum, Min, Max
from django.utils import timezone
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.catalog.permissions import IsInstructorOrAdmin
from .models import (
    InteractiveFormation, FormationSession, FormationEnrollment,
    FormationAttendance, FormationSignal, FormationStatus,
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


def _can_access_session(user, session):
    if _is_organizer(user, session.formation):
        return True
    return FormationEnrollment.objects.filter(user=user, formation=session.formation).exists()


def _role_for(user, formation):
    if user.role == "admin" and user.id not in (formation.instructor_id, formation.co_instructor_id):
        return FormationAttendance.Role.ADMIN
    if user.id in (formation.instructor_id, formation.co_instructor_id):
        return FormationAttendance.Role.ORGANIZER
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
        return qs.filter(
            Q(formation__instructor=user) | Q(formation__co_instructor=user) | Q(formation_id__in=enrolled_ids)
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
            "user": {
                "id": request.user.id,
                "name": request.user.get_full_name() or request.user.username,
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
            old.close()

        attendance = FormationAttendance.objects.create(
            session=session, user=request.user, role=_role_for(request.user, session.formation)
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
            })
        return Response(people)

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
            try:
                recipient = User.objects.get(id=recipient_id)
            except User.DoesNotExist:
                return Response({"recipient_id": ["Participant introuvable."]}, status=400)
            if not _can_access_session(recipient, session):
                return Response({"recipient_id": ["Ce participant n'a pas accès à la séance."]}, status=400)
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

        for attendance in FormationAttendance.objects.filter(session=session, left_at__isnull=True):
            attendance.close(now)
        session.signals.all().delete()

        if not session.formation.sessions.filter(completed=False).exists():
            session.formation.status = FormationStatus.COMPLETED
            session.formation.save(update_fields=["status"])
        return Response(FormationSessionSerializer(session, context=self.get_serializer_context()).data)

    @action(detail=True, methods=["get"])
    def report(self, request, pk=None):
        session = self.get_object()
        self._require_organizer(request, session)
        _close_stale_attendances(session)
        rows = (
            FormationAttendance.objects.filter(session=session)
            .values("user_id", "user__first_name", "user__last_name", "user__username", "user__email", "role")
            .annotate(
                first_join=Min("joined_at"), last_leave=Max("left_at"), total_seconds=Sum("duration_seconds")
            )
            .order_by("first_join")
        )
        organizers = [session.formation.instructor]
        if session.formation.co_instructor:
            organizers.append(session.formation.co_instructor)
        return Response({
            "session": FormationSessionSerializer(session, context=self.get_serializer_context()).data,
            "organizers": [
                {"id": u.id, "name": u.get_full_name() or u.username, "email": u.email} for u in organizers
            ],
            "participants": [
                {
                    "user_id": r["user_id"],
                    "name": (f'{r["user__first_name"]} {r["user__last_name"]}'.strip() or r["user__username"]),
                    "email": r["user__email"],
                    "role": r["role"],
                    "first_join": r["first_join"],
                    "last_leave": r["last_leave"],
                    "total_seconds": r["total_seconds"] or 0,
                }
                for r in rows
            ],
        })


class MyFormationsViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FormationEnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return FormationEnrollment.objects.filter(user=self.request.user).select_related("formation", "formation__instructor", "formation__co_instructor", "formation__category")
