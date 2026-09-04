from __future__ import annotations

from pathlib import Path
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
import json
from rest_framework import serializers

from apps.common.countries import canonical_country_name
from apps.common.fields import RelativeImageField
from apps.common.media_metadata import validate_upload_limits
from apps.payments.models import Currency
from .models import EmployerProfile, CandidateProfile, Opportunity, OpportunityApplication
from .services import clean_strings, match_opportunity, build_application_snapshot, candidate_skills_for


def validate_country(value, *, allow_blank=True):
    text = str(value or "").strip()
    if not text and allow_blank:
        return ""
    try:
        return canonical_country_name(text)
    except ValueError as exc:
        raise serializers.ValidationError(str(exc))


class EmployerPublicSerializer(serializers.ModelSerializer):
    logo = RelativeImageField(read_only=True)

    class Meta:
        model = EmployerProfile
        fields = ["id", "company_name", "slug", "description", "industry", "company_size", "website_url", "logo", "country", "city"]


class EmployerProfileSerializer(serializers.ModelSerializer):
    logo = RelativeImageField(required=False, allow_null=True)
    reviewed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = EmployerProfile
        fields = [
            "id", "company_name", "slug", "description", "industry", "company_size", "website_url", "logo", "country", "city",
            "status", "review_note", "reviewed_by_name", "reviewed_at", "created_at", "updated_at",
        ]
        read_only_fields = ["slug", "status", "review_note", "reviewed_by_name", "reviewed_at", "created_at", "updated_at"]

    def get_reviewed_by_name(self, obj):
        return (obj.reviewed_by.get_full_name() or obj.reviewed_by.username) if obj.reviewed_by else ""

    def validate_country(self, value):
        return validate_country(value, allow_blank=False)

    def validate_logo(self, value):
        if value:
            validate_upload_limits(
                value,
                max_bytes=settings.MAX_IMAGE_UPLOAD_MB * 1024 * 1024,
                extensions={".jpg", ".jpeg", ".png", ".webp", ".avif"},
                field="logo",
            )
        return value


class CandidateProfileSerializer(serializers.ModelSerializer):
    resume_url = serializers.SerializerMethodField()
    portfolio_slug = serializers.SerializerMethodField()

    class Meta:
        model = CandidateProfile
        fields = [
            "id", "headline", "summary", "skills", "desired_roles", "preferred_kinds", "preferred_work_modes", "preferred_countries",
            "minimum_salary", "salary_currency", "availability", "years_experience", "resume", "resume_url", "is_searchable", "portfolio_slug", "updated_at",
        ]
        read_only_fields = ["updated_at", "resume_url", "portfolio_slug"]
        extra_kwargs = {"resume": {"write_only": True, "required": False, "allow_null": True}}

    def to_internal_value(self, data):
        if hasattr(data, "copy"):
            data = data.copy()
        try:
            if data.get("minimum_salary") == "":
                data["minimum_salary"] = None
        except Exception:
            pass
        return super().to_internal_value(data)

    def get_resume_url(self, obj):
        return f"/api/opportunities/candidate-profile/resume/" if obj.resume else None

    def get_portfolio_slug(self, obj):
        try:
            return obj.user.portfolio_profile.slug
        except Exception:
            return ""

    def validate_skills(self, value):
        try:
            return clean_strings(value, max_items=60, max_length=100)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))

    def validate_desired_roles(self, value):
        try:
            return clean_strings(value, max_items=20, max_length=120)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))

    def validate_preferred_kinds(self, value):
        try:
            values = clean_strings(value, max_items=4, max_length=20)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))
        allowed = {choice for choice, _label in Opportunity.Kind.choices}
        invalid = [item for item in values if item not in allowed]
        if invalid:
            raise serializers.ValidationError(f"Types d'opportunités invalides : {', '.join(invalid)}")
        return values

    def validate_preferred_work_modes(self, value):
        try:
            values = clean_strings(value, max_items=3, max_length=20)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))
        allowed = {choice for choice, _label in Opportunity.WorkMode.choices}
        invalid = [item for item in values if item not in allowed]
        if invalid:
            raise serializers.ValidationError(f"Modes de travail invalides : {', '.join(invalid)}")
        return values

    def validate_preferred_countries(self, value):
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except Exception:
                value = [value]
        if not isinstance(value, list):
            raise serializers.ValidationError("Une liste de pays est attendue.")
        result = []
        for item in value[:20]:
            country = validate_country(item, allow_blank=False)
            if country not in result:
                result.append(country)
        return result

    def validate_minimum_salary(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("La rémunération minimale ne peut pas être négative.")
        return value

    def validate_salary_currency(self, value):
        code = str(value or "").strip().upper()
        if not Currency.objects.filter(code=code, is_active=True).exists():
            raise serializers.ValidationError("Sélectionnez une devise active dans LearnEas.")
        return code

    def validate_resume(self, value):
        if value:
            validate_upload_limits(
                value,
                max_bytes=10 * 1024 * 1024,
                extensions={".pdf", ".doc", ".docx"},
                field="resume",
            )
        return value


class OpportunitySerializer(serializers.ModelSerializer):
    employer = EmployerPublicSerializer(read_only=True)
    applications_count = serializers.IntegerField(read_only=True)
    match_score = serializers.SerializerMethodField()
    already_applied = serializers.SerializerMethodField()
    is_open = serializers.BooleanField(read_only=True)

    class Meta:
        model = Opportunity
        fields = [
            "id", "employer", "title", "slug", "kind", "contract_type", "work_mode", "experience_level", "description",
            "responsibilities", "requirements", "skills_required", "skills_optional", "country", "city", "remote_worldwide",
            "salary_min", "salary_max", "salary_currency", "salary_period", "show_salary", "apply_mode", "external_application_url",
            "application_deadline", "status", "featured", "published_at", "created_at", "updated_at", "applications_count",
            "match_score", "already_applied", "is_open",
        ]
        read_only_fields = ["employer", "slug", "featured", "published_at", "created_at", "updated_at", "applications_count"]

    def _request_user(self):
        request = self.context.get("request")
        return request.user if request and request.user.is_authenticated else None

    def _candidate_context(self):
        cached = self.context.get("_opportunity_candidate_context")
        if cached is not None:
            return cached
        user = self._request_user()
        if not user:
            cached = {"user": None, "profile": None, "skills": [], "applied_ids": set()}
        else:
            try:
                profile = user.candidate_profile
            except CandidateProfile.DoesNotExist:
                profile = None
            cached = {
                "user": user,
                "profile": profile,
                # Ces trois familles de données étaient auparavant relues pour CHAQUE offre.
                "skills": candidate_skills_for(user, profile),
                "applied_ids": set(
                    OpportunityApplication.objects.filter(candidate=user)
                    .values_list("opportunity_id", flat=True)
                ),
            }
        self.context["_opportunity_candidate_context"] = cached
        return cached

    def get_match_score(self, obj):
        ctx = self._candidate_context()
        user = ctx["user"]
        return match_opportunity(obj, user, ctx["profile"], ctx["skills"]) if user else None

    def get_already_applied(self, obj):
        ctx = self._candidate_context()
        return bool(ctx["user"] and obj.id in ctx["applied_ids"])

    def validate_country(self, value):
        return validate_country(value, allow_blank=True)

    def validate_responsibilities(self, value):
        try:
            return clean_strings(value, max_items=30, max_length=240)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))

    validate_requirements = validate_responsibilities

    def validate_skills_required(self, value):
        try:
            return clean_strings(value, max_items=40, max_length=100)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))

    validate_skills_optional = validate_skills_required

    def validate_salary_currency(self, value):
        code = str(value or "").strip().upper()
        if not Currency.objects.filter(code=code, is_active=True).exists():
            raise serializers.ValidationError("Sélectionnez une devise active dans LearnEas.")
        return code

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        can_see_private_salary = bool(
            request and request.user.is_authenticated and (
                request.user.role == "admin" or instance.employer.user_id == request.user.id
            )
        )
        if not instance.show_salary and not can_see_private_salary:
            data["salary_min"] = None
            data["salary_max"] = None
        return data

    def validate(self, attrs):
        salary_min = attrs.get("salary_min", getattr(self.instance, "salary_min", None))
        salary_max = attrs.get("salary_max", getattr(self.instance, "salary_max", None))
        if salary_min is not None and salary_min < 0:
            raise serializers.ValidationError({"salary_min": "La rémunération ne peut pas être négative."})
        if salary_max is not None and salary_max < 0:
            raise serializers.ValidationError({"salary_max": "La rémunération ne peut pas être négative."})
        if salary_min is not None and salary_max is not None and salary_min > salary_max:
            raise serializers.ValidationError({"salary_max": "Le salaire maximal doit être supérieur ou égal au minimum."})

        apply_mode = attrs.get("apply_mode", getattr(self.instance, "apply_mode", Opportunity.ApplyMode.INTERNAL))
        external_url = attrs.get("external_application_url", getattr(self.instance, "external_application_url", ""))
        if apply_mode == Opportunity.ApplyMode.EXTERNAL and not external_url:
            raise serializers.ValidationError({"external_application_url": "Le lien de candidature externe est obligatoire."})
        if apply_mode == Opportunity.ApplyMode.INTERNAL:
            attrs["external_application_url"] = ""

        remote_worldwide = attrs.get("remote_worldwide", getattr(self.instance, "remote_worldwide", False))
        if remote_worldwide:
            attrs["country"] = ""
            attrs["city"] = ""
        else:
            country = attrs.get("country", getattr(self.instance, "country", ""))
            if not country:
                raise serializers.ValidationError({"country": "Sélectionnez le pays de l'opportunité."})

        deadline = attrs.get("application_deadline", getattr(self.instance, "application_deadline", None))
        target_status = attrs.get("status", getattr(self.instance, "status", Opportunity.Status.DRAFT))
        if target_status == Opportunity.Status.PUBLISHED and deadline and deadline <= timezone.now():
            raise serializers.ValidationError({"application_deadline": "La date limite doit être dans le futur pour publier."})
        return attrs


class OpportunityApplicationSerializer(serializers.ModelSerializer):
    opportunity_title = serializers.CharField(source="opportunity.title", read_only=True)
    opportunity_slug = serializers.CharField(source="opportunity.slug", read_only=True)
    company_name = serializers.CharField(source="opportunity.employer.company_name", read_only=True)
    resume_url = serializers.SerializerMethodField()

    class Meta:
        model = OpportunityApplication
        fields = [
            "id", "opportunity", "opportunity_title", "opportunity_slug", "company_name", "status", "cover_letter", "resume_file",
            "resume_url", "share_portfolio", "match_score", "candidate_name_snapshot", "candidate_email_snapshot", "country_snapshot",
            "headline_snapshot", "skills_snapshot", "portfolio_snapshot", "certificates_snapshot", "verified_projects_snapshot",
            "recruiter_note", "applied_at", "updated_at",
        ]
        read_only_fields = [
            "status", "match_score", "candidate_name_snapshot", "candidate_email_snapshot", "country_snapshot", "headline_snapshot",
            "skills_snapshot", "portfolio_snapshot", "certificates_snapshot", "verified_projects_snapshot", "recruiter_note", "applied_at", "updated_at",
        ]
        extra_kwargs = {"resume_file": {"write_only": True, "required": False, "allow_null": True}}

    def get_resume_url(self, obj):
        return f"/api/opportunities/applications/{obj.id}/resume/" if obj.resume_file else None

    def validate_resume_file(self, value):
        if value:
            validate_upload_limits(value, max_bytes=10 * 1024 * 1024, extensions={".pdf", ".doc", ".docx"}, field="resume_file")
        return value

    def create(self, validated_data):
        request = self.context["request"]
        opportunity = validated_data["opportunity"]
        # Si le candidat utilise son CV de profil, on en copie une version dans la
        # candidature. Le recruteur verra ainsi le CV réellement transmis au moment T,
        # même si le profil candidat est modifié plus tard.
        if not validated_data.get("resume_file"):
            try:
                source = request.user.candidate_profile.resume
            except Exception:
                source = None
            try:
                if source and source.size <= 10 * 1024 * 1024:
                    source.open("rb")
                    content = source.read()
                    source.close()
                    filename = Path(source.name).name or f"cv-{request.user.id}.pdf"
                    validated_data["resume_file"] = ContentFile(content, name=filename)
            except Exception:
                # Le CV est facultatif : une indisponibilité du stockage ne doit pas
                # empêcher la candidature elle-même.
                validated_data.pop("resume_file", None)
        snapshot = build_application_snapshot(request.user, opportunity, share_portfolio=validated_data.get("share_portfolio", True))
        return OpportunityApplication.objects.create(candidate=request.user, **validated_data, **snapshot)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        is_owner_recruiter = bool(
            request and request.user.is_authenticated and (
                request.user.role == "admin" or instance.opportunity.employer.user_id == request.user.id
            )
        )
        if not is_owner_recruiter:
            data.pop("recruiter_note", None)
            # L'email n'est transmis au recruteur qu'après candidature, jamais dans la recherche publique talents.
        return data


class ApplicationReviewSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[
        OpportunityApplication.Status.REVIEWING, OpportunityApplication.Status.SHORTLISTED,
        OpportunityApplication.Status.INTERVIEW, OpportunityApplication.Status.OFFER,
        OpportunityApplication.Status.HIRED, OpportunityApplication.Status.REJECTED,
    ])
    recruiter_note = serializers.CharField(required=False, allow_blank=True, max_length=5000)


class TalentSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    country = serializers.CharField(source="user.country", read_only=True)
    avatar = RelativeImageField(source="user.avatar", read_only=True)
    portfolio_slug = serializers.SerializerMethodField()

    class Meta:
        model = CandidateProfile
        fields = ["id", "full_name", "avatar", "country", "headline", "summary", "skills", "desired_roles", "availability", "years_experience", "portfolio_slug", "updated_at"]

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def get_portfolio_slug(self, obj):
        try:
            portfolio = obj.user.portfolio_profile
            return portfolio.slug if portfolio.is_public else ""
        except Exception:
            return ""
