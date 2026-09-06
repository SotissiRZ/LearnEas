from __future__ import annotations

from django.db import models, transaction
from django.db.models import Count, Q, Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status, viewsets, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend

from apps.enrollments.models import CourseEnrollment
from .models import ProjectAssignment, ProjectSubmission, ProjectSubmissionRevision, PortfolioProfile, PortfolioItem
from .serializers import (
    ProjectAssignmentSerializer, ProjectSubmissionSerializer, ProjectReviewSerializer,
    PortfolioProfileSerializer, PortfolioItemSerializer, PublicPortfolioSerializer,
)
from .services import ensure_portfolio_profile, publish_verified_submission, refresh_enrollment_after_project


class ProjectSubmissionPagination(PageNumberPagination):
    page_size = 30
    page_size_query_param = "page_size"
    max_page_size = 100


class ProjectAssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        qs = ProjectAssignment.objects.select_related("course", "course__instructor").annotate(
            submissions_count=Count("submissions", distinct=True),
            awaiting_review_count=Count("submissions", filter=Q(submissions__status=ProjectSubmission.Status.SUBMITTED), distinct=True),
        )
        if user.role == "admin":
            return qs
        if user.role == "instructor":
            return qs.filter(course__instructor=user)
        course_ids = CourseEnrollment.objects.filter(user=user).values_list("course_id", flat=True)
        # Les anciennes SerializerMethodField faisaient deux requêtes par projet (inscription +
        # remise). On charge une fois l'inscription du viewer et ses remises, quelle que soit la
        # taille de la liste.
        return qs.filter(course_id__in=course_ids, published=True).prefetch_related(
            Prefetch(
                "course__enrollments",
                queryset=CourseEnrollment.objects.filter(user=user).only("id", "course_id", "purchased_at"),
                to_attr="_viewer_enrollments",
            ),
            Prefetch(
                "submissions",
                queryset=ProjectSubmission.objects.filter(student=user).select_related(
                    "assignment", "assignment__course", "student", "enrollment", "reviewed_by"
                ).prefetch_related("revisions"),
                to_attr="_viewer_submissions",
            ),
        )

    def create(self, request, *args, **kwargs):
        if request.user.role not in ("instructor", "admin"):
            return Response({"detail": "Compte instructeur requis."}, status=403)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if request.user.role not in ("instructor", "admin"):
            return Response({"detail": "Compte instructeur requis."}, status=403)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        assignment = self.get_object()
        if request.user.role not in ("instructor", "admin"):
            return Response({"detail": "Compte instructeur requis."}, status=403)
        if assignment.submissions.exists():
            return Response(
                {"detail": "Ce projet possède déjà des remises. Archivez-le en désactivant sa publication au lieu de le supprimer."},
                status=409,
            )
        return super().destroy(request, *args, **kwargs)


class ProjectSubmissionViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = ProjectSubmissionPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "assignment", "assignment__course"]
    search_fields = ["student__email", "student__first_name", "student__last_name", "assignment__title", "assignment__course__title"]
    ordering_fields = ["submitted_at", "reviewed_at", "updated_at", "score"]
    ordering = ["-updated_at"]

    def get_queryset(self):
        user = self.request.user
        qs = ProjectSubmission.objects.select_related(
            "assignment", "assignment__course", "assignment__course__instructor", "student", "enrollment", "reviewed_by"
        ).prefetch_related("revisions")
        if user.role == "admin":
            return qs
        if user.role == "instructor":
            return qs.filter(assignment__course__instructor=user)
        return qs.filter(student=user)

    def create(self, request, *args, **kwargs):
        assignment_id = request.data.get("assignment")
        existing = ProjectSubmission.objects.filter(assignment_id=assignment_id, student=request.user).first()
        if existing:
            return Response(self.get_serializer(existing).data, status=200)
        return super().create(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        submission = self.get_object()
        if request.user != submission.student or submission.status != ProjectSubmission.Status.DRAFT:
            return Response({"detail": "Seul un brouillon non remis peut être supprimé."}, status=409)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def submit(self, request, pk=None):
        submission = self.get_object()
        if request.user != submission.student:
            return Response({"detail": "Accès refusé."}, status=403)
        if submission.status not in (
            ProjectSubmission.Status.DRAFT, ProjectSubmission.Status.CHANGES_REQUESTED, ProjectSubmission.Status.REJECTED
        ):
            return Response({"detail": "Cette remise est déjà en cours de correction."}, status=409)
        if submission.status != ProjectSubmission.Status.DRAFT:
            assignment = submission.assignment
            if not assignment.allow_resubmission:
                return Response({"detail": "Les nouvelles remises sont désactivées pour ce projet."}, status=409)
            if assignment.max_resubmissions is not None and submission.resubmission_count >= assignment.max_resubmissions:
                return Response({"detail": "Le nombre maximal de nouvelles remises est atteint."}, status=409)
        if not (submission.summary.strip() or submission.external_url or submission.repository_url or submission.artifact_file):
            return Response({"detail": "Ajoutez une description, un lien ou un fichier avant de remettre le projet."}, status=400)

        revision_number = (submission.revisions.aggregate(v=models.Max("revision_number"))["v"] or 0) + 1
        ProjectSubmissionRevision.objects.create(
            submission=submission,
            revision_number=revision_number,
            title=submission.title,
            summary=submission.summary,
            external_url=submission.external_url,
            repository_url=submission.repository_url,
            artifact_file=submission.artifact_file,
            cover_image=submission.cover_image,
            skills=submission.skills,
            submitted_at=timezone.now(),
        )
        if revision_number > 1:
            submission.resubmission_count += 1
        submission.status = ProjectSubmission.Status.SUBMITTED
        submission.submitted_at = timezone.now()
        submission.reviewed_at = None
        submission.reviewed_by = None
        submission.save(update_fields=[
            "status", "submitted_at", "reviewed_at", "reviewed_by", "resubmission_count", "updated_at"
        ])
        return Response(self.get_serializer(submission).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def review(self, request, pk=None):
        submission = self.get_object()
        if request.user.role != "admin" and submission.assignment.course.instructor_id != request.user.id:
            return Response({"detail": "Vous n'êtes pas autorisé à corriger ce projet."}, status=403)
        if submission.status != ProjectSubmission.Status.SUBMITTED:
            return Response({"detail": "Seules les remises en attente peuvent être corrigées."}, status=409)
        serializer = ProjectReviewSerializer(data=request.data, context={"submission": submission})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        submission.status = data["status"]
        submission.score = data["score"]
        submission.instructor_feedback = data.get("feedback", "").strip()
        submission.reviewed_by = request.user
        submission.reviewed_at = timezone.now()
        submission.save(update_fields=["status", "score", "instructor_feedback", "reviewed_by", "reviewed_at", "updated_at"])
        refresh_enrollment_after_project(submission.enrollment)
        return Response(self.get_serializer(submission).data)

    @action(detail=True, methods=["post"], url_path="publish-portfolio")
    def publish_portfolio(self, request, pk=None):
        submission = self.get_object()
        if request.user != submission.student:
            return Response({"detail": "Accès refusé."}, status=403)
        try:
            item = publish_verified_submission(submission)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(PortfolioItemSerializer(item, context={"request": request}).data, status=201)


class PortfolioProfileViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["get", "patch"])
    def me(self, request):
        profile = ensure_portfolio_profile(request.user)
        if request.method == "PATCH":
            serializer = PortfolioProfileSerializer(profile, data=request.data, partial=True, context={"request": request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
        else:
            serializer = PortfolioProfileSerializer(profile, context={"request": request})
        return Response(serializer.data)


class PortfolioItemViewSet(viewsets.ModelViewSet):
    serializer_class = PortfolioItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return PortfolioItem.objects.filter(owner=self.request.user).select_related(
            "source_submission", "source_submission__assignment"
        )

    def perform_create(self, serializer):
        ensure_portfolio_profile(self.request.user)
        serializer.save()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_verified:
            # La preuve de validation KalanPro est immuable ; l'apprenant ne peut modifier
            # que la présentation et la visibilité de l'élément.
            allowed = {
                "title", "description", "role", "problem", "objective", "outcome", "stack", "video_url",
                "started_at", "completed_at", "cover_image", "is_public", "featured", "order"
            }
            forbidden = set(request.data.keys()) - allowed
            if forbidden:
                return Response({"detail": "Les informations vérifiées d'un projet KalanPro ne peuvent pas être altérées."}, status=409)
        return super().update(request, *args, **kwargs)


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def public_portfolio(request, slug):
    profile = get_object_or_404(
        PortfolioProfile.objects.select_related("user").prefetch_related("certificate_selections__certificate"), slug=slug, is_public=True
    )
    return Response(PublicPortfolioSerializer(profile, context={"request": request}).data)
