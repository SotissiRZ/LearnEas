from __future__ import annotations

from django.db import transaction
from django.db.models import Avg, Count, Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .models import EmployerProfile, CandidateProfile, Opportunity, OpportunityApplication, TalentBookmark
from .serializers import (
    EmployerPublicSerializer, EmployerProfileSerializer, CandidateProfileSerializer, OpportunitySerializer,
    OpportunityApplicationSerializer, ApplicationReviewSerializer, TalentSerializer, TalentBookmarkSerializer,
)


class OpportunityPagination(PageNumberPagination):
    page_size = 18
    page_size_query_param = "page_size"
    max_page_size = 100


def approved_employer_for(user):
    if not getattr(user, "is_authenticated", False) or user.role != "employer":
        return None
    return EmployerProfile.objects.filter(user=user, status=EmployerProfile.Status.APPROVED).first()


class EmployerProfileViewSet(viewsets.ModelViewSet):
    serializer_class = EmployerProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        if self.request.user.role == "admin":
            return EmployerProfile.objects.select_related("user", "reviewed_by").all()
        if self.request.user.role != "employer":
            return EmployerProfile.objects.none()
        return EmployerProfile.objects.select_related("user", "reviewed_by").filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        if request.user.role not in {"admin", "employer"}:
            return Response({"detail": "Compte entreprise / recruteur requis."}, status=403)
        profile = self.get_queryset().filter(user=request.user).first() if request.user.role != "admin" else None
        if request.user.role == "admin":
            return super().list(request, *args, **kwargs)
        return Response(EmployerProfileSerializer(profile, context={"request": request}).data if profile else {"status": "none"})

    def create(self, request, *args, **kwargs):
        if request.user.role != "employer":
            return Response({"detail": "Compte entreprise / recruteur requis."}, status=403)
        existing = EmployerProfile.objects.filter(user=request.user).first()
        if existing:
            if existing.status == EmployerProfile.Status.PENDING:
                return Response({"detail": "Une demande recruteur est déjà en attente."}, status=409)
            serializer = self.get_serializer(existing, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save(status=EmployerProfile.Status.PENDING, review_note="", reviewed_by=None, reviewed_at=None)
            return Response(self.get_serializer(instance).data)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(user=request.user)
        return Response(self.get_serializer(instance).data, status=201)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user.role != "admin" and instance.user_id != request.user.id:
            return Response({"detail": "Accès refusé."}, status=403)

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        sensitive_fields = {"company_name", "country"}
        identity_changed = any(
            field in serializer.validated_data
            and serializer.validated_data[field] != getattr(instance, field)
            for field in sensitive_fields
        )
        if request.user.role != "admin" and instance.status == EmployerProfile.Status.REJECTED:
            # Une entreprise refusée peut corriger son dossier puis le renvoyer.
            serializer.save(
                status=EmployerProfile.Status.PENDING,
                review_note="",
                reviewed_by=None,
                reviewed_at=None,
            )
        elif request.user.role != "admin" and instance.status == EmployerProfile.Status.APPROVED and identity_changed:
            # Un recruteur approuvé ne peut pas remplacer son identité par celle d'une autre
            # entreprise sans contrôle. Le profil et ses offres disparaissent du public jusqu'à
            # une nouvelle validation administrateur (les candidatures historiques sont conservées).
            serializer.save(
                status=EmployerProfile.Status.PENDING,
                review_note="",
                reviewed_by=None,
                reviewed_at=None,
            )
        else:
            serializer.save()
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        if request.user.role != "admin":
            return Response({"detail": "Administrateur requis."}, status=403)
        profile = self.get_object()
        profile.status = EmployerProfile.Status.APPROVED
        profile.review_note = str(request.data.get("review_note") or "").strip()
        profile.reviewed_by = request.user
        profile.reviewed_at = timezone.now()
        profile.save(update_fields=["status", "review_note", "reviewed_by", "reviewed_at", "updated_at"])
        return Response(self.get_serializer(profile).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        if request.user.role != "admin":
            return Response({"detail": "Administrateur requis."}, status=403)
        profile = self.get_object()
        profile.status = EmployerProfile.Status.REJECTED
        profile.review_note = str(request.data.get("review_note") or "").strip()
        profile.reviewed_by = request.user
        profile.reviewed_at = timezone.now()
        profile.save(update_fields=["status", "review_note", "reviewed_by", "reviewed_at", "updated_at"])
        return Response(self.get_serializer(profile).data)

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        if request.user.role != "admin":
            return Response({"detail": "Administrateur requis."}, status=403)
        profile = self.get_object()
        profile.status = EmployerProfile.Status.SUSPENDED
        profile.review_note = str(request.data.get("review_note") or "").strip()
        profile.reviewed_by = request.user
        profile.reviewed_at = timezone.now()
        profile.save(update_fields=["status", "review_note", "reviewed_by", "reviewed_at", "updated_at"])
        Opportunity.objects.filter(employer=profile, status=Opportunity.Status.PUBLISHED).update(status=Opportunity.Status.CLOSED)
        return Response(self.get_serializer(profile).data)


    @action(detail=False, methods=["get"])
    def analytics(self, request):
        employer = approved_employer_for(request.user)
        if not employer:
            return Response({"detail": "Espace recruteur approuvé requis."}, status=403)
        jobs = Opportunity.objects.filter(employer=employer)
        applications = OpportunityApplication.objects.filter(opportunity__employer=employer)
        by_status = {
            row["status"]: row["count"]
            for row in applications.values("status").annotate(count=Count("id"))
        }
        jobs_by_status = {
            row["status"]: row["count"]
            for row in jobs.values("status").annotate(count=Count("id"))
        }
        average_match = applications.aggregate(value=Avg("match_score"))["value"] or 0
        return Response({
            "opportunities_total": jobs.count(),
            "published": jobs_by_status.get(Opportunity.Status.PUBLISHED, 0),
            "drafts": jobs_by_status.get(Opportunity.Status.DRAFT, 0),
            "applications_total": applications.count(),
            "pipeline": by_status,
            "shortlisted": by_status.get(OpportunityApplication.Status.SHORTLISTED, 0),
            "interviews": by_status.get(OpportunityApplication.Status.INTERVIEW, 0),
            "offers": by_status.get(OpportunityApplication.Status.OFFER, 0),
            "hires": by_status.get(OpportunityApplication.Status.HIRED, 0),
            "average_match": round(float(average_match), 1),
            "bookmarked_talents": TalentBookmark.objects.filter(employer=employer).count(),
        })


class EmployerDirectoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EmployerPublicSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"
    pagination_class = OpportunityPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["company_name", "tagline", "description", "industry", "country", "city"]
    ordering_fields = ["company_name", "created_at"]
    ordering = ["company_name"]

    def get_queryset(self):
        return EmployerProfile.objects.filter(status=EmployerProfile.Status.APPROVED).annotate(
            open_opportunities_count=Count(
                "opportunities",
                filter=(
                    Q(opportunities__status=Opportunity.Status.PUBLISHED)
                    & (Q(opportunities__application_deadline__isnull=True) | Q(opportunities__application_deadline__gt=timezone.now()))
                ),
                distinct=True,
            )
        )


class CandidateProfileViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        if request.user.role == "employer":
            return Response({"detail": "Un compte recruteur ne possède pas de profil candidat."}, status=403)
        profile, _ = CandidateProfile.objects.get_or_create(user=request.user)
        return Response(CandidateProfileSerializer(profile, context={"request": request}).data)

    def partial_update(self, request, pk=None):
        if request.user.role == "employer":
            return Response({"detail": "Un compte recruteur ne possède pas de profil candidat."}, status=403)
        profile, _ = CandidateProfile.objects.get_or_create(user=request.user)
        serializer = CandidateProfileSerializer(profile, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=["patch"], url_path="me")
    def me(self, request):
        return self.partial_update(request)

    @action(detail=False, methods=["get"], url_path="resume")
    def resume(self, request):
        profile = get_object_or_404(CandidateProfile, user=request.user)
        if not profile.resume:
            return Response({"detail": "Aucun CV."}, status=404)
        response = FileResponse(profile.resume.open("rb"), as_attachment=True, filename=profile.resume.name.rsplit("/", 1)[-1])
        response["Cache-Control"] = "private, no-store"
        return response


class OpportunityViewSet(viewsets.ModelViewSet):
    serializer_class = OpportunitySerializer
    pagination_class = OpportunityPagination
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["kind", "contract_type", "work_mode", "experience_level", "featured", "status"]
    search_fields = ["title", "description", "skills_required", "skills_optional", "employer__company_name", "employer__industry", "city", "country"]
    ordering_fields = ["published_at", "created_at", "application_deadline", "salary_min", "salary_max"]
    ordering = ["-featured", "-published_at"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = Opportunity.objects.select_related("employer", "employer__user").annotate(applications_count=Count("applications", distinct=True))
        if self.action in ("list", "retrieve"):
            if user.is_authenticated and user.role == "admin" and self.request.query_params.get("admin") == "1":
                return qs
            if user.is_authenticated and self.request.query_params.get("mine") == "1":
                employer = EmployerProfile.objects.filter(user=user).first()
                return qs.filter(employer=employer) if employer else qs.none()
            public_qs = qs.filter(status=Opportunity.Status.PUBLISHED, employer__status=EmployerProfile.Status.APPROVED).filter(
                Q(application_deadline__isnull=True) | Q(application_deadline__gt=timezone.now())
            )
            country = str(self.request.query_params.get("country") or "").strip()
            if country:
                public_qs = public_qs.filter(Q(country=country) | Q(remote_worldwide=True))
            employer_slug = str(self.request.query_params.get("employer") or "").strip()
            if employer_slug:
                public_qs = public_qs.filter(employer__slug=employer_slug)
            return public_qs
        if user.role == "admin":
            return qs
        employer = approved_employer_for(user)
        return qs.filter(employer=employer) if employer else qs.none()

    def perform_create(self, serializer):
        employer = approved_employer_for(self.request.user)
        if not employer and self.request.user.role != "admin":
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Votre espace recruteur doit être approuvé avant de publier.")
        if self.request.user.role == "admin":
            employer_id = self.request.data.get("employer_id")
            employer = get_object_or_404(EmployerProfile, pk=employer_id, status=EmployerProfile.Status.APPROVED)
        serializer.save(employer=employer)

    def perform_update(self, serializer):
        instance = serializer.instance
        if self.request.user.role != "admin" and instance.employer.user_id != self.request.user.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Accès refusé.")
        if serializer.validated_data.get("status") == Opportunity.Status.PUBLISHED and instance.employer.status != EmployerProfile.Status.APPROVED:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Entreprise non approuvée.")
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        opportunity = self.get_object()
        if opportunity.applications.exists():
            return Response({"detail": "Cette opportunité possède des candidatures. Clôturez ou archivez-la au lieu de la supprimer."}, status=409)
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def matches(self, request):
        qs = self.filter_queryset(
            Opportunity.objects.select_related("employer", "employer__user").filter(
                status=Opportunity.Status.PUBLISHED, employer__status=EmployerProfile.Status.APPROVED
            ).filter(Q(application_deadline__isnull=True) | Q(application_deadline__gt=timezone.now()))
        )
        serializer = self.get_serializer(qs[:100], many=True)
        rows = sorted(serializer.data, key=lambda row: (row.get("match_score") or 0, bool(row.get("featured"))), reverse=True)
        return Response(rows[:30])


class ApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = OpportunityApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = OpportunityPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "opportunity"]
    search_fields = ["candidate_name_snapshot", "candidate_email_snapshot", "headline_snapshot", "skills_snapshot", "opportunity__title"]
    ordering_fields = ["applied_at", "match_score", "updated_at"]
    ordering = ["-applied_at"]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        qs = OpportunityApplication.objects.select_related("candidate", "opportunity", "opportunity__employer", "opportunity__employer__user")
        if user.role == "admin":
            return qs
        employer = approved_employer_for(user)
        if employer and (self.request.query_params.get("recruiter") == "1" or self.action == "review"):
            return qs.filter(opportunity__employer=employer)
        if employer and self.action == "resume":
            return qs.filter(Q(candidate=user) | Q(opportunity__employer=employer))
        return qs.filter(candidate=user)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        if request.user.role == "employer":
            return Response({"detail": "Un compte recruteur ne peut pas déposer de candidature."}, status=403)
        opportunity = get_object_or_404(Opportunity.objects.select_for_update(), pk=request.data.get("opportunity"))
        if opportunity.apply_mode != Opportunity.ApplyMode.INTERNAL:
            return Response({"detail": "Cette opportunité utilise une candidature externe."}, status=409)
        if opportunity.employer.user_id == request.user.id:
            return Response({"detail": "Vous ne pouvez pas candidater à une opportunité publiée par votre propre entreprise."}, status=409)
        if not opportunity.is_open or opportunity.employer.status != EmployerProfile.Status.APPROVED:
            return Response({"detail": "Les candidatures sont clôturées pour cette opportunité."}, status=409)
        if OpportunityApplication.objects.filter(opportunity=opportunity, candidate=request.user).exists():
            return Response({"detail": "Vous avez déjà candidaté à cette opportunité."}, status=409)
        data = request.data.copy()
        data["opportunity"] = opportunity.id
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        application = serializer.save()
        return Response(self.get_serializer(application).data, status=201)

    @action(detail=True, methods=["post"])
    def withdraw(self, request, pk=None):
        application = self.get_object()
        if application.candidate_id != request.user.id:
            return Response({"detail": "Accès refusé."}, status=403)
        if application.status in {OpportunityApplication.Status.HIRED, OpportunityApplication.Status.REJECTED, OpportunityApplication.Status.WITHDRAWN}:
            return Response({"detail": "Cette candidature ne peut plus être retirée."}, status=409)
        application.status = OpportunityApplication.Status.WITHDRAWN
        application.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(application).data)

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        application = self.get_object()
        if request.user.role != "admin" and application.opportunity.employer.user_id != request.user.id:
            return Response({"detail": "Accès recruteur requis."}, status=403)
        if application.status == OpportunityApplication.Status.WITHDRAWN:
            return Response({"detail": "Le candidat a retiré cette candidature."}, status=409)
        serializer = ApplicationReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_status = serializer.validated_data["status"]
        if (
            request.user.role != "admin"
            and application.status in {OpportunityApplication.Status.HIRED, OpportunityApplication.Status.REJECTED}
            and target_status != application.status
        ):
            return Response({"detail": "Cette candidature est dans un état final et ne peut plus changer d'étape."}, status=409)
        application.status = target_status
        update_fields = ["status", "updated_at"]
        for field in ("recruiter_note", "recruiter_rating", "recruiter_tags", "next_step_at"):
            if field in serializer.validated_data:
                setattr(application, field, serializer.validated_data[field])
                update_fields.append(field)
        application.save(update_fields=update_fields)
        return Response(self.get_serializer(application).data)

    @action(detail=True, methods=["get"])
    def resume(self, request, pk=None):
        application = self.get_object()
        recruiter = request.user.role == "admin" or application.opportunity.employer.user_id == request.user.id
        candidate = application.candidate_id == request.user.id
        if not (recruiter or candidate):
            return Response({"detail": "Accès refusé."}, status=403)
        file_field = application.resume_file
        if not file_field:
            return Response({"detail": "Aucun CV disponible."}, status=404)
        response = FileResponse(file_field.open("rb"), as_attachment=True, filename=file_field.name.rsplit("/", 1)[-1])
        response["Cache-Control"] = "private, no-store"
        return response


class TalentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TalentSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = OpportunityPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["headline", "summary", "skills", "desired_roles", "user__first_name", "user__last_name", "user__country"]
    ordering_fields = ["updated_at", "years_experience"]
    ordering = ["-updated_at"]

    def get_queryset(self):
        if not (self.request.user.role == "admin" or approved_employer_for(self.request.user)):
            return CandidateProfile.objects.none()
        qs = CandidateProfile.objects.select_related("user").filter(is_searchable=True)
        country = str(self.request.query_params.get("country") or "").strip()
        availability = str(self.request.query_params.get("availability") or "").strip()
        min_experience = str(self.request.query_params.get("min_experience") or "").strip()
        if country:
            qs = qs.filter(user__country=country)
        if availability:
            qs = qs.filter(availability=availability)
        if min_experience.isdigit():
            qs = qs.filter(years_experience__gte=int(min_experience))
        return qs


class TalentBookmarkViewSet(viewsets.ModelViewSet):
    serializer_class = TalentBookmarkSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        employer = approved_employer_for(self.request.user)
        if not employer:
            return TalentBookmark.objects.none()
        return TalentBookmark.objects.select_related("talent", "talent__user").filter(employer=employer)

    def perform_create(self, serializer):
        employer = approved_employer_for(self.request.user)
        if not employer:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Espace recruteur approuvé requis.")
        talent = serializer.validated_data["talent"]
        if not talent.is_searchable:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"talent": "Ce talent n'est plus visible aux recruteurs."})
        existing = TalentBookmark.objects.filter(employer=employer, talent=talent).first()
        if existing:
            serializer.instance = existing
            serializer.save(employer=employer, talent=talent)
            return
        serializer.save(employer=employer)
