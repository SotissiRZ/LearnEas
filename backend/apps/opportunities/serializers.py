from __future__ import annotations

from pathlib import Path
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from django.db.models import Q
import json
from rest_framework import serializers

from apps.common.countries import canonical_country_name
from apps.common.fields import RelativeImageField
from apps.common.media_metadata import validate_upload_limits
from apps.payments.models import Currency
from .models import (
    EmployerProfile, CandidateProfile, Opportunity, OpportunityApplication, TalentBookmark,
    TalentAccessLog, EmployerEntitlement, ApplicationHistoryEvent, RecruitmentInterview, EmploymentOffer,
)
from .services import clean_strings, match_opportunity, build_application_snapshot, candidate_skills_for


def validate_country(value, *, allow_blank=True):
    text = str(value or "").strip()
    if not text and allow_blank:
        return ""
    try:
        return canonical_country_name(text)
    except ValueError as exc:
        raise serializers.ValidationError(str(exc))


def _shallow_mutable_input(data):
    """Clone superficiellement les données DRF multipart sans copier les fichiers.

    ``QueryDict.copy()`` fait un ``deepcopy`` et casse sur
    ``TemporaryUploadedFile`` (flux ``BufferedRandom`` non picklable). En plus,
    conserver un ``MultiValueDict`` après avoir converti nos champs JSON en
    listes Python fait que DRF continue de les traiter comme des valeurs HTML et
    tente de les décoder une seconde fois comme JSON.

    Une ``dict`` Python ordinaire résout les deux problèmes : les objets fichiers
    sont conservés par référence et les listes JSON déjà décodées sont transmises
    directement aux ``JSONField``. Comme ``QueryDict.get()``/``items()`` utilisent
    la dernière valeur pour une clé, cette conversion garde la sémantique des
    formulaires KalanPro, qui envoient un seul champ par clé.
    """
    if hasattr(data, "items"):
        return {key: value for key, value in data.items()}
    if isinstance(data, dict):
        return dict(data)
    return data


class EmployerPublicSerializer(serializers.ModelSerializer):
    logo = RelativeImageField(read_only=True)
    banner = RelativeImageField(read_only=True)
    open_opportunities_count = serializers.SerializerMethodField()

    class Meta:
        model = EmployerProfile
        fields = [
            "id", "company_name", "slug", "tagline", "description", "industry", "company_size",
            "website_url", "linkedin_url", "logo", "banner", "brand_color", "founded_year",
            "values", "benefits", "hiring_regions", "country", "city", "open_opportunities_count",
        ]

    def get_open_opportunities_count(self, obj):
        annotated = getattr(obj, "open_opportunities_count", None)
        if annotated is not None:
            return annotated
        # Ce serializer est imbriqué dans chaque offre. Sans cache, la même entreprise
        # déclencherait un COUNT SQL supplémentaire pour chaque ligne de la liste.
        cache = self.context.setdefault("_employer_open_opportunities_count", {})
        if obj.pk not in cache:
            cache[obj.pk] = obj.opportunities.filter(status=Opportunity.Status.PUBLISHED).filter(
                Q(application_deadline__isnull=True) | Q(application_deadline__gt=timezone.now())
            ).count()
        return cache[obj.pk]


class EmployerProfileSerializer(serializers.ModelSerializer):
    logo = RelativeImageField(required=False, allow_null=True)
    banner = RelativeImageField(required=False, allow_null=True)
    reviewed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = EmployerProfile
        fields = [
            "id", "company_name", "slug", "tagline", "description", "industry", "company_size", "website_url",
            "linkedin_url", "contact_email", "founded_year", "brand_color", "logo", "banner", "values", "benefits",
            "hiring_regions", "country", "city", "status", "review_note", "reviewed_by_name", "reviewed_at", "created_at", "updated_at",
        ]
        read_only_fields = ["slug", "status", "review_note", "reviewed_by_name", "reviewed_at", "created_at", "updated_at"]

    def to_internal_value(self, data):
        data = _shallow_mutable_input(data)
        for field in ("values", "benefits", "hiring_regions"):
            try:
                value = data.get(field)
            except Exception:
                value = None
            if isinstance(value, str):
                try:
                    data[field] = json.loads(value)
                except Exception:
                    data[field] = [part.strip() for part in value.replace(";", ",").split(",") if part.strip()]
        try:
            if data.get("founded_year") == "":
                data["founded_year"] = None
        except Exception:
            pass
        return super().to_internal_value(data)

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

    def validate_banner(self, value):
        if value:
            validate_upload_limits(
                value,
                max_bytes=settings.MAX_IMAGE_UPLOAD_MB * 1024 * 1024,
                extensions={".jpg", ".jpeg", ".png", ".webp", ".avif"},
                field="banner",
            )
        return value

    def validate_brand_color(self, value):
        color = str(value or "").strip() or "#ff5a1f"
        import re
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
            raise serializers.ValidationError("Utilisez une couleur hexadécimale, ex. #FF5A1F.")
        return color.lower()

    def validate_founded_year(self, value):
        if value is not None and (value < 1800 or value > timezone.now().year):
            raise serializers.ValidationError("Année de création invalide.")
        return value

    def _validate_strings(self, value, *, max_items=30, max_length=160):
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except Exception:
                value = [part.strip() for part in value.replace(";", ",").split(",") if part.strip()]
        try:
            return clean_strings(value, max_items=max_items, max_length=max_length)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))

    def validate_values(self, value):
        return self._validate_strings(value, max_items=12, max_length=120)

    def validate_benefits(self, value):
        return self._validate_strings(value, max_items=20, max_length=160)

    def validate_hiring_regions(self, value):
        return self._validate_strings(value, max_items=20, max_length=120)


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
        data = _shallow_mutable_input(data)
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
            raise serializers.ValidationError("Sélectionnez une devise active dans KalanPro.")
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
    cover_image = RelativeImageField(required=False, allow_null=True)
    remove_cover_image = serializers.BooleanField(write_only=True, required=False, default=False)
    applications_count = serializers.IntegerField(read_only=True)
    match_score = serializers.SerializerMethodField()
    already_applied = serializers.SerializerMethodField()
    is_open = serializers.BooleanField(read_only=True)

    class Meta:
        model = Opportunity
        fields = [
            "id", "employer", "title", "slug", "kind", "contract_type", "work_mode", "experience_level", "description",
            "department", "openings", "cover_image", "remove_cover_image", "responsibilities", "requirements", "skills_required", "skills_optional",
            "screening_questions", "country", "city", "remote_worldwide",
            "salary_min", "salary_max", "salary_currency", "salary_period", "show_salary", "apply_mode", "external_application_url",
            "application_deadline", "status", "featured", "published_at", "created_at", "updated_at", "applications_count",
            "match_score", "already_applied", "is_open",
        ]
        read_only_fields = ["employer", "slug", "featured", "published_at", "created_at", "updated_at", "applications_count"]

    def to_internal_value(self, data):
        data = _shallow_mutable_input(data)
        for field in ("responsibilities", "requirements", "skills_required", "skills_optional", "screening_questions"):
            try:
                value = data.get(field)
            except Exception:
                value = None
            if isinstance(value, str):
                try:
                    data[field] = json.loads(value)
                except Exception:
                    data[field] = [part.strip() for part in value.replace(";", ",").split(",") if part.strip()]
        for field in ("salary_min", "salary_max", "application_deadline"):
            try:
                if data.get(field) == "":
                    data[field] = None
            except Exception:
                pass
        return super().to_internal_value(data)

    def validate_cover_image(self, value):
        if value:
            validate_upload_limits(
                value,
                max_bytes=settings.MAX_IMAGE_UPLOAD_MB * 1024 * 1024,
                extensions={".jpg", ".jpeg", ".png", ".webp", ".avif"},
                field="cover_image",
            )
        return value

    def validate_screening_questions(self, value):
        try:
            return clean_strings(value, max_items=8, max_length=300)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))

    def validate_openings(self, value):
        if value < 1 or value > 500:
            raise serializers.ValidationError("Le nombre de postes doit être compris entre 1 et 500.")
        return value

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
            raise serializers.ValidationError("Sélectionnez une devise active dans KalanPro.")
        return code

    def create(self, validated_data):
        validated_data.pop("remove_cover_image", None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        remove_cover = bool(validated_data.pop("remove_cover_image", False))
        if remove_cover and instance.cover_image:
            try:
                instance.cover_image.delete(save=False)
            except Exception:
                instance.cover_image = None
            else:
                instance.cover_image = None
        return super().update(instance, validated_data)

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
            "id", "opportunity", "opportunity_title", "opportunity_slug", "company_name", "status", "cover_letter", "screening_answers", "resume_file",
            "resume_url", "share_portfolio", "match_score", "candidate_name_snapshot", "candidate_email_snapshot", "country_snapshot",
            "headline_snapshot", "skills_snapshot", "portfolio_snapshot", "certificates_snapshot", "verified_projects_snapshot",
            "recruiter_note", "recruiter_rating", "recruiter_tags", "next_step_at", "applied_at", "updated_at",
        ]
        read_only_fields = [
            "status", "match_score", "candidate_name_snapshot", "candidate_email_snapshot", "country_snapshot", "headline_snapshot",
            "skills_snapshot", "portfolio_snapshot", "certificates_snapshot", "verified_projects_snapshot", "recruiter_note",
            "recruiter_rating", "recruiter_tags", "next_step_at", "applied_at", "updated_at",
        ]
        extra_kwargs = {"resume_file": {"write_only": True, "required": False, "allow_null": True}}

    def to_internal_value(self, data):
        data = _shallow_mutable_input(data)
        try:
            value = data.get("screening_answers")
        except Exception:
            value = None
        if isinstance(value, str):
            try:
                data["screening_answers"] = json.loads(value)
            except Exception:
                data["screening_answers"] = []
        return super().to_internal_value(data)

    def get_resume_url(self, obj):
        return f"/api/opportunities/applications/{obj.id}/resume/" if obj.resume_file else None

    def validate_resume_file(self, value):
        if value:
            validate_upload_limits(value, max_bytes=10 * 1024 * 1024, extensions={".pdf", ".doc", ".docx"}, field="resume_file")
        return value

    def validate_screening_answers(self, value):
        opportunity = None
        try:
            raw_id = self.initial_data.get("opportunity")
            opportunity = Opportunity.objects.filter(pk=raw_id).first()
        except Exception:
            opportunity = None
        if not isinstance(value, list):
            raise serializers.ValidationError("Une liste de réponses est attendue.")
        questions = opportunity.screening_questions if opportunity else []
        if len(value) > max(8, len(questions)):
            raise serializers.ValidationError("Trop de réponses de présélection.")
        cleaned = []
        for row in value:
            if not isinstance(row, dict):
                raise serializers.ValidationError("Format de réponse invalide.")
            question = str(row.get("question") or "").strip()[:300]
            answer = str(row.get("answer") or "").strip()[:2000]
            if question:
                cleaned.append({"question": question, "answer": answer})
        if questions:
            expected = [str(q).strip() for q in questions]
            if [row["question"] for row in cleaned] != expected:
                raise serializers.ValidationError("Répondez aux questions de l'offre dans l'ordre affiché.")
        return cleaned

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
        if not instance.share_portfolio:
            # Défense en profondeur pour les candidatures historiques créées avant v78 :
            # même si un ancien snapshot contient encore des preuves, l'API ne les expose pas.
            data["portfolio_snapshot"] = {}
            data["certificates_snapshot"] = []
            data["verified_projects_snapshot"] = []
        request = self.context.get("request")
        is_owner_recruiter = bool(
            request and request.user.is_authenticated and (
                request.user.role == "admin" or instance.opportunity.employer.user_id == request.user.id
            )
        )
        if not is_owner_recruiter:
            for field in ("recruiter_note", "recruiter_rating", "recruiter_tags", "next_step_at"):
                data.pop(field, None)
            # L'email n'est transmis au recruteur qu'après candidature, jamais dans la recherche publique talents.
        return data


class ApplicationReviewSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[
        OpportunityApplication.Status.REVIEWING, OpportunityApplication.Status.SHORTLISTED,
        OpportunityApplication.Status.INTERVIEW, OpportunityApplication.Status.OFFER,
        OpportunityApplication.Status.HIRED, OpportunityApplication.Status.REJECTED,
    ])
    recruiter_note = serializers.CharField(required=False, allow_blank=True, max_length=5000)
    recruiter_rating = serializers.IntegerField(required=False, min_value=0, max_value=5)
    recruiter_tags = serializers.ListField(
        child=serializers.CharField(max_length=60), required=False, allow_empty=True, max_length=20
    )
    next_step_at = serializers.DateTimeField(required=False, allow_null=True)

    def validate_recruiter_tags(self, value):
        try:
            return clean_strings(value, max_items=20, max_length=60)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))


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


class TalentBookmarkSerializer(serializers.ModelSerializer):
    talent_detail = TalentSerializer(source="talent", read_only=True)

    class Meta:
        model = TalentBookmark
        fields = ["id", "talent", "talent_detail", "note", "tags", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at", "talent_detail"]

    def validate_tags(self, value):
        try:
            return clean_strings(value, max_items=20, max_length=60)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))


class TalentAccessLogSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="employer.company_name", read_only=True)
    company_slug = serializers.CharField(source="employer.slug", read_only=True)

    class Meta:
        model = TalentAccessLog
        fields = ["id", "company_name", "company_slug", "access_type", "created_at"]


class EmployerEntitlementSerializer(serializers.ModelSerializer):
    current = serializers.SerializerMethodField()
    consumed_opportunity = serializers.SerializerMethodField()

    class Meta:
        model = EmployerEntitlement
        fields = [
            "id", "kind", "entitlement_key", "starts_at", "ends_at", "revoked_at",
            "revocation_reason", "consumed_at", "consumed_opportunity", "current", "created_at",
        ]

    def get_current(self, obj):
        now = timezone.now()
        if obj.revoked_at is not None or obj.order.status != "paid":
            return False
        if obj.kind == EmployerEntitlement.Kind.SINGLE_POST:
            return obj.consumed_at is None or (obj.ends_at is not None and obj.ends_at > now)
        return bool(obj.starts_at and obj.ends_at and obj.starts_at <= now < obj.ends_at)

    def get_consumed_opportunity(self, obj):
        if not obj.consumed_by_id:
            return None
        return {
            "id": obj.consumed_by_id,
            "title": obj.consumed_by.title,
            "slug": obj.consumed_by.slug,
            "status": obj.consumed_by.status,
        }


class ApplicationHistoryEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = ApplicationHistoryEvent
        fields = ["id", "event_type", "label", "metadata", "actor_name", "created_at"]

    def get_actor_name(self, obj):
        if not obj.actor:
            return ""
        return obj.actor.get_full_name() or obj.actor.username


class RecruitmentInterviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecruitmentInterview
        fields = [
            "id", "application", "scheduled_at", "duration_minutes", "mode", "location_or_url",
            "candidate_message", "status", "created_at", "updated_at",
        ]
        read_only_fields = ["application", "created_at", "updated_at"]

    def validate_duration_minutes(self, value):
        if not 10 <= int(value) <= 480:
            raise serializers.ValidationError("La durée doit être comprise entre 10 et 480 minutes.")
        return value

    def validate_scheduled_at(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("L'entretien doit être planifié dans le futur.")
        return value


class EmploymentOfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmploymentOffer
        fields = [
            "id", "application", "title", "message", "salary_amount", "salary_currency",
            "start_date", "expires_at", "status", "responded_at", "created_at", "updated_at",
        ]
        read_only_fields = ["application", "status", "responded_at", "created_at", "updated_at"]

    def validate_salary_currency(self, value):
        code = str(value or "").strip().upper()
        if not Currency.objects.filter(code=code, is_active=True).exists():
            raise serializers.ValidationError("Sélectionnez une devise active dans KalanPro.")
        return code

    def validate_salary_amount(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Le salaire proposé ne peut pas être négatif.")
        return value

    def validate_expires_at(self, value):
        if value and value <= timezone.now():
            raise serializers.ValidationError("La date d'expiration de l'offre doit être dans le futur.")
        return value
