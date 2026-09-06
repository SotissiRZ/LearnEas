from __future__ import annotations

from django.conf import settings
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

from .models import (
    EmployerProfile, CandidateProfile, Opportunity, OpportunityApplication, TalentBookmark,
    TalentAccessLog, EmployerEntitlement, ApplicationHistoryEvent, RecruitmentInterview, EmploymentOffer, SavedTalentSearch,
)
from .serializers import (
    EmployerPublicSerializer, EmployerProfileSerializer, CandidateProfileSerializer, OpportunitySerializer,
    OpportunityApplicationSerializer, ApplicationReviewSerializer, TalentSerializer, TalentBookmarkSerializer,
    TalentAccessLogSerializer, EmployerEntitlementSerializer, ApplicationHistoryEventSerializer,
    RecruitmentInterviewSerializer, EmploymentOfferSerializer, SavedTalentSearchSerializer,
)
from .services import (
    employer_has_talent_pool_access, employer_active_job_limit, current_employer_plan,
    active_employer_entitlements, claim_publication_right, record_application_event,
    match_opportunity_breakdown, apply_talent_search_filters,
)
from apps.notifications.models import InAppNotification
from apps.notifications.services import queue_recruitment_update


class OpportunityPagination(PageNumberPagination):
    page_size = 18
    page_size_query_param = "page_size"
    max_page_size = 100


def approved_employer_for(user):
    if not getattr(user, "is_authenticated", False) or user.role != "employer":
        return None
    return EmployerProfile.objects.filter(user=user, status=EmployerProfile.Status.APPROVED).first()


def queue_recruitment_after_commit(**kwargs):
    # Les tâches externes (Resend/WhatsApp) ne doivent jamais partir avant le commit DB.
    transaction.on_commit(lambda: queue_recruitment_update(**kwargs))


class EmployerProfileViewSet(viewsets.ModelViewSet):
    serializer_class = EmployerProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch", "head", "options"]

    @staticmethod
    def _verification_reset_for_changes(instance, validated_data, *, is_admin=False):
        if is_admin:
            return {}
        identity_fields = {
            "company_name", "country", "legal_name", "registration_number",
            "registration_country", "verification_document",
        }
        changed = any(
            field in validated_data and validated_data[field] != getattr(instance, field)
            for field in identity_fields
        )
        if not changed:
            return {}
        return {
            "verification_status": EmployerProfile.VerificationStatus.UNVERIFIED,
            "verification_note": "",
            "verification_submitted_at": None,
            "identity_verified_at": None,
            "identity_verified_by": None,
        }

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
            verification_reset = self._verification_reset_for_changes(
                existing, serializer.validated_data, is_admin=request.user.role == "admin"
            )
            instance = serializer.save(
                status=EmployerProfile.Status.PENDING, review_note="", reviewed_by=None, reviewed_at=None,
                **verification_reset,
            )
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
        identity_changed = any(
            field in serializer.validated_data
            and serializer.validated_data[field] != getattr(instance, field)
            for field in {"company_name", "country"}
        )
        verification_reset = self._verification_reset_for_changes(
            instance, serializer.validated_data, is_admin=request.user.role == "admin"
        )

        if request.user.role != "admin" and instance.status == EmployerProfile.Status.REJECTED:
            # Une entreprise refusée peut corriger son dossier puis le renvoyer.
            serializer.save(
                status=EmployerProfile.Status.PENDING,
                review_note="",
                reviewed_by=None,
                reviewed_at=None,
                **verification_reset,
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
                **verification_reset,
            )
        else:
            serializer.save(**verification_reset)
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


    @action(detail=True, methods=["post"], url_path="submit-verification")
    def submit_verification(self, request, pk=None):
        profile = self.get_object()
        if request.user.role != "admin" and profile.user_id != request.user.id:
            return Response({"detail": "Accès refusé."}, status=403)
        if not profile.legal_name or not profile.registration_number or not profile.registration_country or not profile.verification_document:
            return Response({
                "detail": "Renseignez la raison sociale, le numéro d'immatriculation, le pays et un justificatif avant l'envoi."
            }, status=400)
        profile.verification_status = EmployerProfile.VerificationStatus.PENDING
        profile.verification_note = ""
        profile.verification_submitted_at = timezone.now()
        profile.identity_verified_at = None
        profile.identity_verified_by = None
        profile.save(update_fields=[
            "verification_status", "verification_note", "verification_submitted_at",
            "identity_verified_at", "identity_verified_by", "updated_at",
        ])
        return Response(self.get_serializer(profile).data)

    @action(detail=True, methods=["post"], url_path="verify-identity")
    def verify_identity(self, request, pk=None):
        if request.user.role != "admin":
            return Response({"detail": "Administrateur requis."}, status=403)
        profile = self.get_object()
        if not profile.legal_name or not profile.registration_number or not profile.registration_country or not profile.verification_document:
            return Response({"detail": "Le dossier légal est incomplet et ne peut pas être vérifié."}, status=400)
        profile.verification_status = EmployerProfile.VerificationStatus.VERIFIED
        profile.verification_note = str(request.data.get("verification_note") or "").strip()
        profile.identity_verified_at = timezone.now()
        profile.identity_verified_by = request.user
        profile.save(update_fields=[
            "verification_status", "verification_note", "identity_verified_at", "identity_verified_by", "updated_at"
        ])
        return Response(self.get_serializer(profile).data)

    @action(detail=True, methods=["post"], url_path="reject-identity")
    def reject_identity(self, request, pk=None):
        if request.user.role != "admin":
            return Response({"detail": "Administrateur requis."}, status=403)
        profile = self.get_object()
        profile.verification_status = EmployerProfile.VerificationStatus.REJECTED
        profile.verification_note = str(request.data.get("verification_note") or "").strip()
        profile.identity_verified_at = None
        profile.identity_verified_by = None
        profile.save(update_fields=[
            "verification_status", "verification_note", "identity_verified_at", "identity_verified_by", "updated_at"
        ])
        return Response(self.get_serializer(profile).data)


    @action(detail=False, methods=["get"], url_path="commercial-access")
    def commercial_access(self, request):
        employer = approved_employer_for(request.user)
        if not employer:
            return Response({"detail": "Espace recruteur approuvé requis."}, status=403)
        now = timezone.now()
        entitlements = active_employer_entitlements(employer, now=now).select_related(
            "order", "consumed_by"
        ).order_by("starts_at", "created_at")
        return Response({
            "plan": current_employer_plan(employer, now=now),
            "active_job_limit": employer_active_job_limit(employer, now=now),
            "talent_pool": employer_has_talent_pool_access(employer, now=now),
            "unused_single_post_credits": entitlements.filter(
                kind=EmployerEntitlement.Kind.SINGLE_POST,
                consumed_at__isnull=True,
            ).count(),
            "entitlements": EmployerEntitlementSerializer(entitlements, many=True).data,
        })

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

    @action(detail=False, methods=["get"], url_path="talent-accesses")
    def talent_accesses(self, request):
        if request.user.role == "employer":
            return Response({"detail": "Un compte recruteur ne possède pas de journal candidat."}, status=403)
        profile, _ = CandidateProfile.objects.get_or_create(user=request.user)
        logs = profile.access_logs.select_related("employer").all()[:100]
        return Response(TalentAccessLogSerializer(logs, many=True).data)


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

    @transaction.atomic
    def perform_create(self, serializer):
        employer = approved_employer_for(self.request.user)
        if not employer and self.request.user.role != "admin":
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Votre espace recruteur doit être approuvé avant de publier.")
        if self.request.user.role == "admin":
            employer_id = self.request.data.get("employer_id")
            employer = get_object_or_404(EmployerProfile, pk=employer_id, status=EmployerProfile.Status.APPROVED)

        target_status = serializer.validated_data.get("status", Opportunity.Status.DRAFT)
        requested_deadline = serializer.validated_data.get("application_deadline")
        if target_status != Opportunity.Status.PUBLISHED or self.request.user.role == "admin":
            serializer.save(employer=employer)
            return

        # Créer d'abord en brouillon permet d'attacher atomiquement un éventuel crédit
        # d'annonce à l'unité à la ligne concrète sans publier brièvement hors quota.
        instance = serializer.save(employer=employer, status=Opportunity.Status.DRAFT)
        try:
            entitlement, effective_deadline = claim_publication_right(
                employer, opportunity=instance, requested_deadline=requested_deadline
            )
        except ValueError as exc:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"status": str(exc)})
        instance.status = Opportunity.Status.PUBLISHED
        instance.publication_entitlement = entitlement
        if effective_deadline is not None:
            instance.application_deadline = effective_deadline
        instance.save(update_fields=[
            "status", "publication_entitlement", "application_deadline", "published_at", "updated_at"
        ])

    @transaction.atomic
    def perform_update(self, serializer):
        instance = serializer.instance
        if self.request.user.role != "admin" and instance.employer.user_id != self.request.user.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Accès refusé.")
        target_status = serializer.validated_data.get("status", instance.status)
        if target_status == Opportunity.Status.PUBLISHED and instance.employer.status != EmployerProfile.Status.APPROVED:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Entreprise non approuvée.")

        if self.request.user.role == "admin" or target_status != Opportunity.Status.PUBLISHED:
            serializer.save()
            return

        requested_deadline = serializer.validated_data.get("application_deadline", instance.application_deadline)
        existing_credit = instance.publication_entitlement

        # Le plafond de 30 jours doit rester vrai après CHAQUE modification d'une annonce
        # à l'unité déjà publiée. Sans ce contrôle, vider ou repousser la date permettrait
        # de contourner le droit payé après sa consommation.
        if instance.status == Opportunity.Status.PUBLISHED:
            if (
                existing_credit
                and existing_credit.kind == EmployerEntitlement.Kind.SINGLE_POST
                and existing_credit.consumed_by_id == instance.id
            ):
                if existing_credit.revoked_at is not None or not existing_credit.ends_at or existing_credit.ends_at <= timezone.now():
                    from rest_framework.exceptions import ValidationError
                    raise ValidationError({"status": "Le crédit de publication de cette annonce n'est plus actif."})
                if requested_deadline and requested_deadline > existing_credit.ends_at:
                    from rest_framework.exceptions import ValidationError
                    raise ValidationError({"application_deadline": "Cette annonce payée ne peut pas dépasser sa période de 30 jours."})
                updated = serializer.save()
                if updated.application_deadline is None:
                    updated.application_deadline = existing_credit.ends_at
                    updated.save(update_fields=["application_deadline", "updated_at"])
                return
            serializer.save()
            return

        # Une annonce à l'unité déjà consommée peut être republiée uniquement dans sa
        # fenêtre payée restante ; elle ne consomme pas un second crédit.
        if (
            existing_credit
            and existing_credit.kind == EmployerEntitlement.Kind.SINGLE_POST
            and existing_credit.revoked_at is None
            and existing_credit.ends_at
            and existing_credit.ends_at > timezone.now()
            and existing_credit.consumed_by_id == instance.id
        ):
            if requested_deadline and requested_deadline > existing_credit.ends_at:
                from rest_framework.exceptions import ValidationError
                raise ValidationError({"application_deadline": "Cette annonce payée ne peut pas dépasser sa période de 30 jours."})
            updated = serializer.save(status=Opportunity.Status.PUBLISHED)
            if updated.application_deadline is None:
                updated.application_deadline = existing_credit.ends_at
                updated.save(update_fields=["application_deadline", "updated_at"])
            return

        serializer.save(status=Opportunity.Status.DRAFT)
        try:
            entitlement, effective_deadline = claim_publication_right(
                instance.employer, opportunity=instance, requested_deadline=requested_deadline
            )
        except ValueError as exc:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"status": str(exc)})
        instance.status = Opportunity.Status.PUBLISHED
        instance.publication_entitlement = entitlement
        if effective_deadline is not None:
            instance.application_deadline = effective_deadline
        instance.save(update_fields=[
            "status", "publication_entitlement", "application_deadline", "published_at", "updated_at"
        ])

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
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        qs = OpportunityApplication.objects.select_related("candidate", "opportunity", "opportunity__employer", "opportunity__employer__user")
        if user.role == "admin":
            return qs
        employer = approved_employer_for(user)
        recruiter_actions = {"review", "history", "interviews", "offer"}
        if employer and (self.request.query_params.get("recruiter") == "1" or self.action in recruiter_actions):
            return qs.filter(opportunity__employer=employer)
        if employer and self.action == "resume":
            return qs.filter(Q(candidate=user) | Q(opportunity__employer=employer))
        return qs.filter(candidate=user)

    def retrieve(self, request, *args, **kwargs):
        application = self.get_object()
        response = super().retrieve(request, *args, **kwargs)
        employer = approved_employer_for(request.user)
        if employer and application.opportunity.employer_id == employer.id and response.status_code == 200:
            candidate_profile = CandidateProfile.objects.filter(user_id=application.candidate_id).first()
            if candidate_profile:
                TalentAccessLog.objects.create(
                    candidate=candidate_profile, employer=employer, recruiter=request.user,
                    access_type=TalentAccessLog.AccessType.APPLICATION,
                )
        return response

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
        record_application_event(
            application, actor=request.user, event_type="submitted",
            label="Candidature envoyée",
        )
        recruiter = opportunity.employer.user
        recruiter_url = f"{settings.FRONTEND_URL.rstrip('/')}/dashboard/employer"
        queue_recruitment_after_commit(
            user=recruiter, event_key=f"application-submitted:{application.id}",
            title="Nouvelle candidature reçue",
            body=f"{application.candidate_name_snapshot} a candidaté à « {opportunity.title} ».",
            action_url=recruiter_url,
            variables=[recruiter.first_name or recruiter.username, opportunity.title, application.candidate_name_snapshot, recruiter_url],
            metadata={"application_id": application.id, "opportunity_id": opportunity.id},
        )
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
        record_application_event(
            application, actor=request.user, event_type="withdrawn",
            label="Candidature retirée par le candidat",
        )
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
        previous_status = application.status
        application.status = target_status
        update_fields = ["status", "updated_at"]
        for field in ("recruiter_note", "recruiter_rating", "recruiter_tags", "next_step_at"):
            if field in serializer.validated_data:
                setattr(application, field, serializer.validated_data[field])
                update_fields.append(field)
        application.save(update_fields=update_fields)
        if previous_status != target_status:
            record_application_event(
                application, actor=request.user, event_type="status_changed",
                label=f"Étape ATS : {application.get_status_display()}",
                metadata={"from": previous_status, "to": target_status},
            )
            candidate_url = f"{settings.FRONTEND_URL.rstrip('/')}/dashboard/student/opportunities"
            queue_recruitment_after_commit(
                user=application.candidate, event_key=f"application-status:{application.id}:{target_status}",
                title="Mise à jour de votre candidature",
                body=f"« {application.opportunity.title} » est maintenant à l’étape : {application.get_status_display()}.",
                action_url=candidate_url,
                variables=[application.candidate.first_name or application.candidate.username, application.opportunity.title, application.get_status_display(), candidate_url],
                metadata={"application_id": application.id, "status": target_status},
            )
        return Response(self.get_serializer(application).data)

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        application = self.get_object()
        recruiter = request.user.role == "admin" or application.opportunity.employer.user_id == request.user.id
        if not recruiter:
            return Response({"detail": "Accès recruteur requis."}, status=403)
        events = application.history_events.select_related("actor").all()[:100]
        return Response(ApplicationHistoryEventSerializer(events, many=True).data)

    @action(detail=True, methods=["get", "post"])
    @transaction.atomic
    def interviews(self, request, pk=None):
        application = self.get_object()
        recruiter = request.user.role == "admin" or application.opportunity.employer.user_id == request.user.id
        candidate = application.candidate_id == request.user.id
        if request.method == "GET":
            if not (recruiter or candidate):
                return Response({"detail": "Accès refusé."}, status=403)
            rows = application.interviews.all()
            return Response(RecruitmentInterviewSerializer(rows, many=True).data)
        if not recruiter:
            return Response({"detail": "Accès recruteur requis."}, status=403)
        if application.status in {
            OpportunityApplication.Status.WITHDRAWN,
            OpportunityApplication.Status.HIRED,
            OpportunityApplication.Status.REJECTED,
        }:
            return Response({"detail": "Impossible de planifier un entretien sur une candidature clôturée."}, status=409)
        serializer = RecruitmentInterviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        interview = serializer.save(application=application, created_by=request.user)
        previous = application.status
        application.status = OpportunityApplication.Status.INTERVIEW
        application.next_step_at = interview.scheduled_at
        application.save(update_fields=["status", "next_step_at", "updated_at"])
        record_application_event(
            application, actor=request.user, event_type="interview_scheduled",
            label="Entretien planifié",
            metadata={"interview_id": interview.id, "scheduled_at": interview.scheduled_at.isoformat(), "previous_status": previous},
        )
        candidate_url = f"{settings.FRONTEND_URL.rstrip('/')}/dashboard/student/opportunities"
        when = timezone.localtime(interview.scheduled_at).strftime("%d/%m/%Y à %H:%M")
        queue_recruitment_after_commit(
            user=application.candidate, event_key=f"interview-scheduled:{interview.id}",
            title="Entretien planifié",
            body=f"{application.opportunity.title} · {when}", action_url=candidate_url,
            variables=[application.candidate.first_name or application.candidate.username, application.opportunity.title, when, candidate_url],
            metadata={"application_id": application.id, "interview_id": interview.id},
            priority=InAppNotification.Priority.HIGH,
        )
        return Response(RecruitmentInterviewSerializer(interview).data, status=201)

    @action(detail=True, methods=["get", "post", "patch"])
    @transaction.atomic
    def offer(self, request, pk=None):
        application = self.get_object()
        recruiter = request.user.role == "admin" or application.opportunity.employer.user_id == request.user.id
        candidate = application.candidate_id == request.user.id
        existing = EmploymentOffer.objects.filter(application=application).first()

        if request.method == "GET":
            if not (recruiter or candidate):
                return Response({"detail": "Accès refusé."}, status=403)
            if not existing:
                return Response({"detail": "Aucune offre d'embauche."}, status=404)
            return Response(EmploymentOfferSerializer(existing).data)

        if not recruiter:
            return Response({"detail": "Accès recruteur requis."}, status=403)
        if application.status in {
            OpportunityApplication.Status.WITHDRAWN,
            OpportunityApplication.Status.HIRED,
            OpportunityApplication.Status.REJECTED,
        }:
            return Response({"detail": "Cette candidature ne peut plus recevoir une nouvelle offre."}, status=409)
        if existing and existing.status in {EmploymentOffer.Status.ACCEPTED, EmploymentOffer.Status.DECLINED}:
            return Response({"detail": "Cette offre a déjà reçu une réponse et ne peut plus être modifiée."}, status=409)

        serializer = EmploymentOfferSerializer(
            existing, data=request.data, partial=(request.method == "PATCH" or existing is not None)
        )
        serializer.is_valid(raise_exception=True)
        offer = serializer.save(application=application, created_by=existing.created_by if existing else request.user)
        if application.status != OpportunityApplication.Status.OFFER:
            application.status = OpportunityApplication.Status.OFFER
            application.save(update_fields=["status", "updated_at"])
        record_application_event(
            application, actor=request.user,
            event_type="offer_updated" if existing else "offer_created",
            label="Proposition d'embauche mise à jour" if existing else "Proposition d'embauche envoyée",
            metadata={"offer_id": offer.id},
        )
        candidate_url = f"{settings.FRONTEND_URL.rstrip('/')}/dashboard/student/opportunities"
        queue_recruitment_after_commit(
            user=application.candidate, event_key=f"offer:{offer.id}:{offer.updated_at.isoformat()}",
            title="Proposition d’embauche reçue" if not existing else "Proposition d’embauche mise à jour",
            body=f"{application.opportunity.employer.company_name} · {application.opportunity.title}",
            action_url=candidate_url,
            variables=[application.candidate.first_name or application.candidate.username, application.opportunity.title, "Offre d’embauche", candidate_url],
            metadata={"application_id": application.id, "offer_id": offer.id},
            priority=InAppNotification.Priority.HIGH,
        )
        return Response(EmploymentOfferSerializer(offer).data, status=200 if existing else 201)

    @action(detail=True, methods=["post"], url_path="offer-response")
    @transaction.atomic
    def offer_response(self, request, pk=None):
        application = self.get_object()
        if application.candidate_id != request.user.id:
            return Response({"detail": "Seul le candidat peut répondre à cette offre."}, status=403)
        offer = EmploymentOffer.objects.select_for_update().filter(application=application).first()
        if not offer:
            return Response({"detail": "Aucune offre d'embauche."}, status=404)
        if offer.status != EmploymentOffer.Status.PENDING:
            return Response({"detail": "Une réponse a déjà été enregistrée pour cette offre."}, status=409)
        if offer.expires_at and offer.expires_at <= timezone.now():
            return Response({"detail": "Cette offre d'embauche a expiré."}, status=409)
        decision = str(request.data.get("decision") or "").strip().lower()
        if decision not in {EmploymentOffer.Status.ACCEPTED, EmploymentOffer.Status.DECLINED}:
            return Response({"decision": ["Choisissez accepted ou declined."]}, status=400)
        offer.status = decision
        offer.responded_at = timezone.now()
        offer.save(update_fields=["status", "responded_at", "updated_at"])
        application.status = (
            OpportunityApplication.Status.HIRED
            if decision == EmploymentOffer.Status.ACCEPTED
            else OpportunityApplication.Status.REJECTED
        )
        application.save(update_fields=["status", "updated_at"])
        record_application_event(
            application, actor=request.user, event_type=f"offer_{decision}",
            label="Offre acceptée par le candidat" if decision == EmploymentOffer.Status.ACCEPTED else "Offre refusée par le candidat",
            metadata={"offer_id": offer.id},
        )
        recruiter = application.opportunity.employer.user
        recruiter_url = f"{settings.FRONTEND_URL.rstrip('/')}/dashboard/employer"
        decision_label = "acceptée" if decision == EmploymentOffer.Status.ACCEPTED else "refusée"
        queue_recruitment_after_commit(
            user=recruiter, event_key=f"offer-response:{offer.id}:{decision}",
            title=f"Offre d’embauche {decision_label}",
            body=f"{application.candidate_name_snapshot} a {decision_label} votre offre pour « {application.opportunity.title} ».",
            action_url=recruiter_url,
            variables=[recruiter.first_name or recruiter.username, application.opportunity.title, f"Offre {decision_label}", recruiter_url],
            metadata={"application_id": application.id, "offer_id": offer.id, "decision": decision},
            priority=InAppNotification.Priority.HIGH,
        )
        return Response(EmploymentOfferSerializer(offer).data)

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

    def _paid_employer(self):
        employer = approved_employer_for(self.request.user)
        if not employer or not employer_has_talent_pool_access(employer):
            return None
        return employer

    def list(self, request, *args, **kwargs):
        employer = None if request.user.role == "admin" else self._paid_employer()
        if request.user.role != "admin" and not employer:
            return Response({"detail": "Le vivier de talents est réservé aux plans recruteur Pro et Business."}, status=403)
        opportunity = None
        opportunity_id = str(request.query_params.get("opportunity") or "").strip()
        if opportunity_id.isdigit():
            opportunity_qs = Opportunity.objects.select_related("employer").filter(pk=int(opportunity_id))
            if request.user.role != "admin":
                opportunity_qs = opportunity_qs.filter(employer=employer)
            opportunity = opportunity_qs.first()
            if not opportunity:
                return Response({"detail": "Opportunité de matching introuvable."}, status=404)

        qs = self.filter_queryset(self.get_queryset())
        if opportunity:
            rows = list(qs[:500])
            scored = []
            minimum = str(request.query_params.get("min_match_score") or "0").strip()
            minimum = int(minimum) if minimum.isdigit() else 0
            for talent in rows:
                breakdown = match_opportunity_breakdown(opportunity, talent.user, profile=talent)
                if breakdown["total"] >= minimum:
                    scored.append((breakdown["total"], talent))
            scored.sort(key=lambda pair: (pair[0], pair[1].updated_at), reverse=True)
            page = self.paginate_queryset([talent for _score, talent in scored])
            context = {**self.get_serializer_context(), "match_opportunity": opportunity}
            serializer = self.get_serializer(page if page is not None else [talent for _score, talent in scored], many=True, context=context)
            return self.get_paginated_response(serializer.data) if page is not None else Response(serializer.data)
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        employer = None
        if request.user.role != "admin":
            employer = self._paid_employer()
            if not employer:
                return Response({"detail": "Le vivier de talents est réservé aux plans recruteur Pro et Business."}, status=403)
        response = super().retrieve(request, *args, **kwargs)
        if employer and response.status_code == 200:
            talent = self.get_object()
            TalentAccessLog.objects.create(
                candidate=talent, employer=employer, recruiter=request.user,
                access_type=TalentAccessLog.AccessType.PROFILE,
            )
        return response

    def get_queryset(self):
        if self.request.user.role == "admin":
            allowed = True
        else:
            allowed = bool(self._paid_employer())
        if not allowed:
            return CandidateProfile.objects.none()
        qs = CandidateProfile.objects.select_related("user").filter(is_searchable=True)
        return apply_talent_search_filters(
            qs,
            search_text=self.request.query_params.get("search") or "",
            country=self.request.query_params.get("country") or "",
            availability=self.request.query_params.get("availability") or "",
            min_experience=self.request.query_params.get("min_experience") or 0,
        )


class TalentBookmarkViewSet(viewsets.ModelViewSet):
    serializer_class = TalentBookmarkSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        employer = approved_employer_for(self.request.user)
        if not employer or not employer_has_talent_pool_access(employer):
            return TalentBookmark.objects.none()
        return TalentBookmark.objects.select_related("talent", "talent__user").filter(
            employer=employer, talent__is_searchable=True
        )

    def list(self, request, *args, **kwargs):
        employer = approved_employer_for(request.user)
        if not employer or not employer_has_talent_pool_access(employer):
            return Response({"detail": "Les favoris talents sont réservés aux plans recruteur Pro et Business."}, status=403)
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        employer = approved_employer_for(self.request.user)
        if not employer or not employer_has_talent_pool_access(employer):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Un plan recruteur Pro ou Business est requis.")
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
        TalentAccessLog.objects.create(
            candidate=talent, employer=employer, recruiter=self.request.user,
            access_type=TalentAccessLog.AccessType.BOOKMARK,
        )

    def perform_update(self, serializer):
        employer = approved_employer_for(self.request.user)
        if not employer or not employer_has_talent_pool_access(employer):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Un plan recruteur Pro ou Business est requis.")
        talent = serializer.validated_data.get("talent", serializer.instance.talent)
        if not talent.is_searchable:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"talent": "Ce talent n'est plus visible aux recruteurs."})
        if TalentBookmark.objects.filter(employer=employer, talent=talent).exclude(pk=serializer.instance.pk).exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"talent": "Ce talent est déjà présent dans vos favoris."})
        serializer.save(employer=employer, talent=talent)

class SavedTalentSearchViewSet(viewsets.ModelViewSet):
    serializer_class = SavedTalentSearchSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def _employer(self):
        employer = approved_employer_for(self.request.user)
        if not employer or not employer_has_talent_pool_access(employer):
            return None
        return employer

    def get_queryset(self):
        employer = self._employer()
        if not employer:
            return SavedTalentSearch.objects.none()
        return SavedTalentSearch.objects.select_related("opportunity").filter(employer=employer)

    def list(self, request, *args, **kwargs):
        if not self._employer():
            return Response({"detail": "Les recherches sauvegardées sont réservées aux plans recruteur Pro et Business."}, status=403)
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        employer = self._employer()
        if not employer:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Un plan recruteur Pro ou Business est requis.")
        serializer.save(employer=employer, last_checked_at=timezone.now())

    def perform_update(self, serializer):
        employer = self._employer()
        if not employer:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Un plan recruteur Pro ou Business est requis.")
        serializer.save(employer=employer)

