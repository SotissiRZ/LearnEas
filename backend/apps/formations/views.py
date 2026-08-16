from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.catalog.permissions import IsInstructorOrAdmin
from .models import InteractiveFormation, FormationSession, FormationEnrollment
from .serializers import (
    InteractiveFormationListSerializer, InteractiveFormationDetailSerializer,
    InteractiveFormationWriteSerializer, FormationSessionWriteSerializer,
    FormationEnrollmentSerializer,
)


def _enrolled_formation_ids(user):
    if not user or not user.is_authenticated:
        return set()
    return set(FormationEnrollment.objects.filter(user=user).values_list("formation_id", flat=True))


class InteractiveFormationViewSet(viewsets.ModelViewSet):
    """
    Catalogue des formations interactives (en direct, avec un ou deux formateurs).
    Filtres: ?category=<slug>&level=&status=&search=
    """
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
            return qs.filter(instructor=user)
        if user.is_authenticated and user.role == "admin":
            return qs
        if user.is_authenticated and user.role in ("instructor", "admin"):
            from django.db.models import Q
            return qs.filter(Q(published=True) | Q(instructor=user))
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
        qs = self.get_queryset().filter(instructor=request.user)
        serializer = InteractiveFormationListSerializer(qs, many=True, context=self.get_serializer_context())
        return Response(serializer.data)


class FormationSessionViewSet(viewsets.ModelViewSet):
    queryset = FormationSession.objects.all()
    serializer_class = FormationSessionWriteSerializer
    permission_classes = [IsInstructorOrAdmin]
    filterset_fields = ["formation"]


class MyFormationsViewSet(viewsets.ReadOnlyModelViewSet):
    """Formations interactives auxquelles l'utilisateur connecté est inscrit."""
    serializer_class = FormationEnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return FormationEnrollment.objects.filter(user=self.request.user).select_related("formation")
