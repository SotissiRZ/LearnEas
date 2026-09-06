from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.common.fields import RelativeImageField, ProtectedFileField
from apps.common.media_metadata import validate_upload_limits
from apps.enrollments.models import CourseEnrollment
from .models import (
    ProjectAssignment, ProjectSubmission, ProjectSubmissionRevision,
    PortfolioProfile, PortfolioItem, PortfolioCertificate,
)
from .services import ensure_portfolio_profile


def _clean_string_list(value, *, max_items=30, max_length=80):
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise serializers.ValidationError("Une liste est attendue.")
    out = []
    for raw in value[:max_items]:
        text = str(raw).strip()
        if text and text not in out:
            out.append(text[:max_length])
    return out


def _reviewer_can_manage(user, assignment):
    return bool(user.role == "admin" or assignment.course.instructor_id == user.id)


class _NullableDateField(serializers.DateField):
    def to_internal_value(self, value):
        if value in ("", None):
            return None
        return super().to_internal_value(value)


class ProjectAssignmentSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)
    course_slug = serializers.CharField(source="course.slug", read_only=True)
    instructor_name = serializers.SerializerMethodField()
    due_at = serializers.SerializerMethodField()
    submission = serializers.SerializerMethodField()
    submissions_count = serializers.IntegerField(read_only=True, required=False)
    awaiting_review_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = ProjectAssignment
        fields = [
            "id", "course", "course_title", "course_slug", "instructor_name", "title", "slug", "brief",
            "instructions", "objectives", "deliverables", "skills", "due_days_after_enrollment",
            "max_score", "passing_score", "required_for_certificate", "allow_resubmission", "max_resubmissions",
            "published", "order", "due_at", "submission", "submissions_count", "awaiting_review_count",
            "created_at", "updated_at",
        ]
        read_only_fields = ["slug", "created_at", "updated_at"]

    def get_instructor_name(self, obj):
        user = obj.course.instructor
        return user.get_full_name() or user.username

    def get_due_at(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated or not obj.due_days_after_enrollment:
            return None
        prefetched = getattr(obj.course, "_viewer_enrollments", None)
        if prefetched is not None:
            enrollment = prefetched[0] if prefetched else None
        else:
            # Repli utile pour la sérialisation ponctuelle hors ViewSet (admin/tests).
            enrollment = CourseEnrollment.objects.filter(user=request.user, course=obj.course).only("purchased_at").first()
        return enrollment.purchased_at + timedelta(days=obj.due_days_after_enrollment) if enrollment else None

    def get_submission(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated or request.user.role != "student":
            return None
        prefetched = getattr(obj, "_viewer_submissions", None)
        if prefetched is not None:
            submission = prefetched[0] if prefetched else None
        else:
            submission = ProjectSubmission.objects.filter(assignment=obj, student=request.user).select_related(
                "assignment", "assignment__course", "student", "enrollment", "reviewed_by"
            ).prefetch_related("revisions").first()
        return ProjectSubmissionSummarySerializer(submission, context=self.context).data if submission else None

    def validate_objectives(self, value):
        return _clean_string_list(value, max_items=30, max_length=200)

    def validate_deliverables(self, value):
        return _clean_string_list(value, max_items=30, max_length=200)

    def validate_skills(self, value):
        return _clean_string_list(value, max_items=30, max_length=80)

    def validate(self, attrs):
        request = self.context["request"]
        course = attrs.get("course") or getattr(self.instance, "course", None)
        if self.instance and attrs.get("course") and attrs["course"].id != self.instance.course_id:
            raise serializers.ValidationError({"course": "Le cours d'un projet existant ne peut pas être changé."})
        if not course:
            raise serializers.ValidationError({"course": "Cours requis."})
        if request.user.role != "admin" and course.instructor_id != request.user.id:
            raise serializers.ValidationError({"course": "Vous ne pouvez créer des projets que pour vos propres cours."})
        max_score = int(attrs.get("max_score", getattr(self.instance, "max_score", 100)) or 100)
        passing = int(attrs.get("passing_score", getattr(self.instance, "passing_score", 60)) or 0)
        if max_score < 1 or max_score > 1000:
            raise serializers.ValidationError({"max_score": "Le barème doit être compris entre 1 et 1000."})
        if passing < 0 or passing > max_score:
            raise serializers.ValidationError({"passing_score": "La note de validation doit être comprise dans le barème."})
        required = attrs.get("required_for_certificate", getattr(self.instance, "required_for_certificate", False))
        becoming_required = bool(required and (not self.instance or not self.instance.required_for_certificate))
        if becoming_required and course.enrollments.filter(certificate_issued=True).exists():
            raise serializers.ValidationError({
                "required_for_certificate": "Ce cours possède déjà des certificats émis. Le projet ne peut pas devenir rétroactivement obligatoire."
            })
        return attrs

    def _refresh_affected_enrollments(self, assignment):
        from .services import refresh_enrollment_after_project
        for enrollment in assignment.course.enrollments.filter(certificate_issued=False).select_related("course", "user"):
            refresh_enrollment_after_project(enrollment)

    def create(self, validated_data):
        assignment = super().create(validated_data)
        if assignment.required_for_certificate and assignment.published:
            self._refresh_affected_enrollments(assignment)
        return assignment

    def update(self, instance, validated_data):
        old_gate = bool(instance.required_for_certificate and instance.published)
        assignment = super().update(instance, validated_data)
        new_gate = bool(assignment.required_for_certificate and assignment.published)
        if old_gate != new_gate:
            self._refresh_affected_enrollments(assignment)
        return assignment


class ProjectSubmissionRevisionSerializer(serializers.ModelSerializer):
    artifact_file = ProtectedFileField(read_only=True)
    cover_image = RelativeImageField(read_only=True)

    class Meta:
        model = ProjectSubmissionRevision
        fields = [
            "id", "revision_number", "title", "summary", "external_url", "repository_url",
            "artifact_file", "cover_image", "skills", "submitted_at",
        ]


class ProjectSubmissionSummarySerializer(serializers.ModelSerializer):
    assignment_title = serializers.CharField(source="assignment.title", read_only=True)
    course_title = serializers.CharField(source="assignment.course.title", read_only=True)
    artifact_file = ProtectedFileField(read_only=True)
    cover_image = RelativeImageField(read_only=True)
    is_late = serializers.BooleanField(read_only=True)
    can_resubmit = serializers.SerializerMethodField()

    class Meta:
        model = ProjectSubmission
        fields = [
            "id", "assignment", "assignment_title", "course_title", "title", "summary", "external_url",
            "repository_url", "artifact_file", "cover_image", "skills", "status", "score", "instructor_feedback",
            "submitted_at", "reviewed_at", "resubmission_count", "is_late", "can_resubmit", "updated_at",
        ]

    def get_can_resubmit(self, obj):
        if obj.status not in (ProjectSubmission.Status.CHANGES_REQUESTED, ProjectSubmission.Status.REJECTED):
            return False
        assignment = obj.assignment
        if not assignment.allow_resubmission:
            return False
        return assignment.max_resubmissions is None or obj.resubmission_count < assignment.max_resubmissions


class ProjectSubmissionSerializer(ProjectSubmissionSummarySerializer):
    student_name = serializers.SerializerMethodField()
    student_email = serializers.EmailField(source="student.email", read_only=True)
    course_slug = serializers.CharField(source="assignment.course.slug", read_only=True)
    passing_score = serializers.IntegerField(source="assignment.passing_score", read_only=True)
    max_score = serializers.IntegerField(source="assignment.max_score", read_only=True)
    required_for_certificate = serializers.BooleanField(source="assignment.required_for_certificate", read_only=True)
    revisions = ProjectSubmissionRevisionSerializer(many=True, read_only=True)
    artifact_file = ProtectedFileField(required=False, allow_null=True)
    cover_image = RelativeImageField(required=False, allow_null=True)

    class Meta(ProjectSubmissionSummarySerializer.Meta):
        fields = ProjectSubmissionSummarySerializer.Meta.fields + [
            "student_name", "student_email", "course_slug", "passing_score", "max_score",
            "required_for_certificate", "revisions", "enrollment", "student", "reviewed_by",
        ]
        read_only_fields = [
            "enrollment", "student", "status", "score", "instructor_feedback", "submitted_at", "reviewed_at",
            "reviewed_by", "resubmission_count",
        ]

    def get_student_name(self, obj):
        return obj.student.get_full_name() or obj.student.username

    def validate_skills(self, value):
        return _clean_string_list(value, max_items=30, max_length=80)

    def validate(self, attrs):
        request = self.context["request"]
        if request.user.role != "student":
            raise serializers.ValidationError("Seul un apprenant peut remettre un projet.")
        assignment = attrs.get("assignment") or getattr(self.instance, "assignment", None)
        if self.instance and attrs.get("assignment") and attrs["assignment"].id != self.instance.assignment_id:
            raise serializers.ValidationError({"assignment": "Le projet d'une remise existante ne peut pas être changé."})
        if not assignment or not assignment.published:
            raise serializers.ValidationError({"assignment": "Projet indisponible."})
        enrollment = CourseEnrollment.objects.filter(user=request.user, course=assignment.course).first()
        if not enrollment:
            raise serializers.ValidationError({"assignment": "Vous devez être inscrit à ce cours."})
        if self.instance and self.instance.status not in (
            ProjectSubmission.Status.DRAFT, ProjectSubmission.Status.CHANGES_REQUESTED, ProjectSubmission.Status.REJECTED
        ):
            raise serializers.ValidationError("Cette remise est verrouillée pendant sa correction.")
        if self.instance and self.instance.status in (ProjectSubmission.Status.CHANGES_REQUESTED, ProjectSubmission.Status.REJECTED):
            if not assignment.allow_resubmission:
                raise serializers.ValidationError("Les nouvelles remises sont désactivées pour ce projet.")
            if assignment.max_resubmissions is not None and self.instance.resubmission_count >= assignment.max_resubmissions:
                raise serializers.ValidationError("Le nombre maximal de nouvelles remises est atteint.")
        artifact = attrs.get("artifact_file")
        if artifact:
            max_mb = int(getattr(settings, "MAX_PROJECT_UPLOAD_MB", 50))
            validate_upload_limits(
                artifact,
                max_bytes=max_mb * 1024 * 1024,
                extensions={".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip", ".txt", ".csv", ".png", ".jpg", ".jpeg", ".webp"},
                field="artifact_file",
            )
        cover = attrs.get("cover_image")
        if cover:
            validate_upload_limits(
                cover,
                max_bytes=settings.MAX_IMAGE_UPLOAD_MB * 1024 * 1024,
                extensions={".jpg", ".jpeg", ".png", ".webp", ".avif"},
                field="cover_image",
            )
        attrs["_enrollment"] = enrollment
        return attrs

    def create(self, validated_data):
        enrollment = validated_data.pop("_enrollment")
        return ProjectSubmission.objects.create(
            enrollment=enrollment, student=self.context["request"].user, **validated_data
        )

    def update(self, instance, validated_data):
        validated_data.pop("_enrollment", None)
        return super().update(instance, validated_data)


class ProjectReviewSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[
        ProjectSubmission.Status.APPROVED,
        ProjectSubmission.Status.CHANGES_REQUESTED,
        ProjectSubmission.Status.REJECTED,
    ])
    score = serializers.DecimalField(max_digits=6, decimal_places=2)
    feedback = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        submission = self.context["submission"]
        score = attrs["score"]
        if score < 0 or score > submission.assignment.max_score:
            raise serializers.ValidationError({"score": f"La note doit être comprise entre 0 et {submission.assignment.max_score}."})
        if attrs["status"] == ProjectSubmission.Status.APPROVED and score < submission.assignment.passing_score:
            raise serializers.ValidationError({
                "status": f"Une validation nécessite au moins {submission.assignment.passing_score}/{submission.assignment.max_score}."
            })
        if attrs["status"] in (ProjectSubmission.Status.CHANGES_REQUESTED, ProjectSubmission.Status.REJECTED) and not attrs.get("feedback", "").strip():
            raise serializers.ValidationError({"feedback": "Expliquez à l'apprenant ce qui doit être corrigé."})
        return attrs


class PortfolioProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    avatar = RelativeImageField(source="user.avatar", read_only=True)
    country = serializers.CharField(source="user.country", read_only=True)
    user_headline = serializers.CharField(source="user.headline", read_only=True)
    public_url = serializers.SerializerMethodField()
    selected_certificate_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False, write_only=True)
    certificates = serializers.SerializerMethodField()

    class Meta:
        model = PortfolioProfile
        fields = [
            "id", "slug", "is_public", "title", "about", "skills", "website_url", "linkedin_url", "github_url",
            "open_to_work", "show_country", "show_project_scores", "show_certificates", "public_contact_email", "show_contact_email",
            "full_name", "avatar", "country", "user_headline", "public_url", "selected_certificate_ids", "certificates", "updated_at",
        ]
        read_only_fields = ["updated_at"]

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def get_public_url(self, obj):
        base = str(getattr(settings, "FRONTEND_URL", "")).rstrip("/")
        return f"{base}/portfolio/{obj.slug}" if base else f"/portfolio/{obj.slug}"

    def validate_slug(self, value):
        value = value.strip().lower()
        if len(value) < 3:
            raise serializers.ValidationError("Le lien public doit contenir au moins 3 caractères.")
        reserved = {"admin", "api", "dashboard", "login", "register", "portfolio", "courses", "formations", "mentorship"}
        if value in reserved:
            raise serializers.ValidationError("Ce lien public est réservé.")
        return value

    def validate_skills(self, value):
        return _clean_string_list(value, max_items=40, max_length=80)

    def validate_selected_certificate_ids(self, value):
        from apps.enrollments.models import Certificate
        ordered = []
        seen = set()
        for raw in value:
            certificate_id = int(raw)
            if certificate_id not in seen:
                ordered.append(certificate_id)
                seen.add(certificate_id)
        request = self.context.get("request")
        user = getattr(request, "user", None)
        owned = set(Certificate.objects.filter(user=user, id__in=ordered).values_list("id", flat=True)) if user else set()
        if owned != set(ordered):
            raise serializers.ValidationError("Un certificat sélectionné ne vous appartient pas ou n'existe pas.")
        return ordered

    def get_certificates(self, obj):
        selections = obj.certificate_selections.select_related("certificate").order_by("-featured", "order", "-created_at")
        result = []
        for selection in selections:
            cert = selection.certificate
            result.append({
                "id": cert.id,
                "certificate_number": cert.certificate_number,
                "content_title": cert.content_title,
                "effective_status": cert.effective_status,
                "issued_at": cert.issued_at,
                "expires_at": cert.expires_at,
                "featured": selection.featured,
                "order": selection.order,
                "is_public": selection.is_public,
            })
        return result

    def update(self, instance, validated_data):
        selected_ids = validated_data.pop("selected_certificate_ids", None)
        instance = super().update(instance, validated_data)
        if selected_ids is not None:
            PortfolioCertificate.objects.filter(profile=instance).exclude(certificate_id__in=selected_ids).delete()
            existing = set(PortfolioCertificate.objects.filter(profile=instance, certificate_id__in=selected_ids).values_list("certificate_id", flat=True))
            PortfolioCertificate.objects.bulk_create([
                PortfolioCertificate(profile=instance, certificate_id=certificate_id, order=index)
                for index, certificate_id in enumerate(selected_ids) if certificate_id not in existing
            ])
            for index, certificate_id in enumerate(selected_ids):
                PortfolioCertificate.objects.filter(profile=instance, certificate_id=certificate_id).update(order=index, is_public=True)
        return instance


class PortfolioItemSerializer(serializers.ModelSerializer):
    started_at = _NullableDateField(required=False, allow_null=True)
    completed_at = _NullableDateField(required=False, allow_null=True)
    cover_image = RelativeImageField(required=False, allow_null=True)
    verified_score_display = serializers.SerializerMethodField()

    class Meta:
        model = PortfolioItem
        fields = [
            "id", "source_submission", "title", "description", "role", "problem", "objective", "outcome", "stack", "video_url",
            "started_at", "completed_at", "cover_image", "external_url", "repository_url", "skills",
            "is_public", "featured", "order", "is_verified", "verified_course_title", "verified_assignment_title",
            "verified_instructor_name", "verified_at", "verified_score", "verified_max_score", "verified_score_display", "created_at", "updated_at",
        ]
        read_only_fields = [
            "source_submission", "is_verified", "verified_course_title", "verified_assignment_title",
            "verified_instructor_name", "verified_at", "verified_score", "verified_max_score", "created_at", "updated_at",
        ]

    def get_verified_score_display(self, obj):
        if not obj.is_verified or obj.verified_score is None:
            return None
        max_score = obj.verified_max_score
        return f"{obj.verified_score:g}/{max_score}" if max_score else str(obj.verified_score)

    def validate_skills(self, value):
        return _clean_string_list(value, max_items=30, max_length=80)

    def validate_stack(self, value):
        return _clean_string_list(value, max_items=30, max_length=80)

    def validate(self, attrs):
        started = attrs.get("started_at", getattr(self.instance, "started_at", None))
        completed = attrs.get("completed_at", getattr(self.instance, "completed_at", None))
        if started and completed and completed < started:
            raise serializers.ValidationError({"completed_at": "La date de fin doit être postérieure à la date de début."})
        return attrs

    def validate_cover_image(self, value):
        if value:
            validate_upload_limits(
                value,
                max_bytes=settings.MAX_IMAGE_UPLOAD_MB * 1024 * 1024,
                extensions={".jpg", ".jpeg", ".png", ".webp", ".avif"},
                field="cover_image",
            )
        return value

    def create(self, validated_data):
        return PortfolioItem.objects.create(owner=self.context["request"].user, **validated_data)


class PublicPortfolioItemSerializer(serializers.ModelSerializer):
    cover_image = RelativeImageField(read_only=True)
    score = serializers.SerializerMethodField()

    class Meta:
        model = PortfolioItem
        fields = [
            "id", "title", "description", "role", "problem", "objective", "outcome", "stack", "video_url",
            "started_at", "completed_at", "cover_image", "external_url", "repository_url", "skills", "featured",
            "is_verified", "verified_course_title", "verified_assignment_title", "verified_instructor_name", "verified_at", "score",
        ]

    def get_score(self, obj):
        profile = self.context.get("profile")
        if not profile or not profile.show_project_scores or not obj.is_verified or obj.verified_score is None:
            return None
        return {"value": float(obj.verified_score), "max": obj.verified_max_score}


class PublicPortfolioSerializer(PortfolioProfileSerializer):
    country = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()
    certificates = serializers.SerializerMethodField()
    contact_email = serializers.SerializerMethodField()

    class Meta(PortfolioProfileSerializer.Meta):
        fields = [
            "slug", "title", "about", "skills", "website_url", "linkedin_url", "github_url", "open_to_work",
            "full_name", "avatar", "country", "user_headline", "contact_email", "items", "certificates", "updated_at",
        ]

    def get_country(self, obj):
        return obj.user.country if obj.show_country else ""

    def get_contact_email(self, obj):
        return obj.public_contact_email if obj.show_contact_email and obj.public_contact_email else ""

    def get_items(self, obj):
        qs = obj.user.portfolio_items.filter(is_public=True).order_by("-featured", "order", "-updated_at")
        return PublicPortfolioItemSerializer(qs, many=True, context={"profile": obj}).data

    def get_certificates(self, obj):
        if not obj.show_certificates:
            return []
        selections = obj.certificate_selections.filter(is_public=True).select_related("certificate").order_by("-featured", "order", "-created_at")
        result = []
        from django.conf import settings as django_settings
        for selection in selections:
            cert = selection.certificate
            if cert.effective_status != cert.Status.ACTIVE:
                continue
            result.append({
                "id": cert.id,
                "certificate_number": cert.certificate_number,
                "content_title": cert.content_title,
                "instructor_name": cert.instructor_name,
                "issuer_name": cert.issuer_name or "KalanPro",
                "issued_at": cert.issued_at,
                "expires_at": cert.expires_at,
                "achievement_percent": cert.achievement_percent,
                "skills": cert.skills_snapshot or [],
                "verification_url": f"{django_settings.FRONTEND_URL.rstrip('/')}/certificates/verify/{cert.verification_code}",
                "featured": selection.featured,
            })
        return result
