from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from apps.common.fields import RelativeImageField
from apps.common.countries import canonical_country_name
from .models import PlatformSettings, InstructorApplication

User = get_user_model()


class UserPublicCompactSerializer(serializers.ModelSerializer):
    """Profil public léger pour les cartes catalogue (aucune requête agrégée)."""
    full_name = serializers.SerializerMethodField()
    avatar = RelativeImageField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "full_name", "avatar", "bio", "headline",
            "domain", "years_experience",
        ]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class UserPublicSerializer(UserPublicCompactSerializer):
    """Profil public détaillé utilisé sur une fiche où le compteur est utile."""
    courses_count = serializers.SerializerMethodField()

    class Meta(UserPublicCompactSerializer.Meta):
        fields = UserPublicCompactSerializer.Meta.fields + ["courses_count"]

    def get_courses_count(self, obj):
        return obj.courses.filter(published=True).count() if hasattr(obj, "courses") else 0


class UserSerializer(serializers.ModelSerializer):
    avatar = RelativeImageField(required=False, allow_null=True)
    technical_admin = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name", "role",
            "avatar", "bio", "country", "headline", "domain",
            "years_experience", "date_joined", "technical_admin",
        ]
        read_only_fields = ["id", "username", "email", "role", "date_joined", "technical_admin"]

    def get_technical_admin(self, obj):
        # L'administration Django expose des données beaucoup plus sensibles que le back-office
        # applicatif. Elle reste donc réservée aux comptes techniques explicitement superuser.
        return bool(obj.role == User.Role.ADMIN and obj.is_staff and obj.is_superuser)

    def validate_country(self, value):
        if not str(value or "").strip():
            return ""
        try:
            return canonical_country_name(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))


class RegisterSerializer(serializers.ModelSerializer):
    country = serializers.CharField(required=True, allow_blank=False, max_length=100)
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "country", "password", "password2"]

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("Un compte existe déjà avec cet email.")
        return email

    def validate_country(self, value):
        try:
            return canonical_country_name(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password2": "Les mots de passe ne correspondent pas."})
        candidate = User(email=attrs.get("email", ""), first_name=attrs.get("first_name", ""), last_name=attrs.get("last_name", ""))
        try:
            validate_password(attrs["password"], user=candidate)
        except Exception as exc:
            raise serializers.ValidationError({"password": list(getattr(exc, "messages", [str(exc)]))})
        return attrs

    def create(self, validated_data):
        from django.utils.text import slugify
        validated_data.pop("password2")
        password = validated_data.pop("password")
        email = validated_data["email"]
        base = slugify(email.split("@", 1)[0]) or "user"
        username = base[:140]
        n = 1
        while User.objects.filter(username__iexact=username).exists():
            n += 1
            suffix = f"-{n}"
            username = f"{base[:150-len(suffix)]}{suffix}"
        user = User(username=username, **validated_data, role=User.Role.STUDENT, is_active=True)
        user.set_password(password)
        user.save()
        return user


class AdminUserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name", "full_name",
            "role", "is_active", "is_staff", "date_joined", "last_login",
            "country", "headline", "domain",
        ]
        read_only_fields = ["id", "username", "email", "is_staff", "date_joined", "last_login", "full_name"]

    def validate_country(self, value):
        if not str(value or "").strip():
            return ""
        try:
            return canonical_country_name(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class AdminUserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "role", "password"]
        read_only_fields = ["id"]

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("Un compte existe déjà avec cet email.")
        return email

    def validate(self, attrs):
        candidate = User(
            email=attrs.get("email", ""),
            first_name=attrs.get("first_name", ""),
            last_name=attrs.get("last_name", ""),
            role=attrs.get("role", User.Role.STUDENT),
        )
        try:
            validate_password(attrs.get("password", ""), user=candidate)
        except Exception as exc:
            raise serializers.ValidationError({"password": list(getattr(exc, "messages", [str(exc)]))})
        return attrs

    def create(self, validated_data):
        from django.utils.text import slugify
        password = validated_data.pop("password")
        email = validated_data["email"]
        base = (slugify(email.split("@")[0]) or "user")[:140]
        username = base
        suffix = 1
        while User.objects.filter(username__iexact=username).exists():
            suffix += 1
            suffix_text = f"-{suffix}"
            username = f"{base[:150-len(suffix_text)]}{suffix_text}"
        user = User(username=username, is_active=True, **validated_data)
        user.set_password(password)
        user.save()
        return user


class PlatformSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformSettings
        fields = [
            "site_name", "support_email", "registration_enabled",
            "instructor_applications_enabled", "platform_commission_percent",
            "minimum_payout_amount",
            "pricing_enabled", "instructor_pro_monthly_eur",
            "instructor_pro_commission_percent", "mentor_commission_percent",
            "employer_free_active_jobs", "employer_single_post_eur",
            "employer_pro_monthly_eur", "employer_pro_active_jobs",
            "employer_business_monthly_eur", "employer_business_active_jobs",
            "legal_company_name", "legal_address", "legal_country",
            "legal_registration_number", "legal_tax_number", "privacy_email",
            "terms_updated_at", "privacy_updated_at", "refund_policy_days",
            "certificate_verification_enabled", "certificate_default_enabled",
            "certificate_default_auto_issue", "certificate_default_threshold_percent",
            "certificate_default_attendance_percent", "certificate_default_validity_months",
            "certificate_default_title", "certificate_default_subtitle",
            "certificate_default_signatory_name", "certificate_default_signatory_title",
            "certificate_default_accent_color", "certificate_default_number_prefix",
            "whatsapp_enabled", "whatsapp_template_language",
            "whatsapp_payment_template_name", "whatsapp_live_template_name",
            "whatsapp_inactivity_template_name", "whatsapp_certificate_template_name",
            "whatsapp_test_template_name", "whatsapp_live_reminder_minutes",
            "whatsapp_inactivity_days",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]

    def validate_legal_country(self, value):
        if not str(value or "").strip():
            return ""
        try:
            return canonical_country_name(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))

    def validate_platform_commission_percent(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("La commission doit être comprise entre 0 et 100 %.")
        return value

    def validate_instructor_pro_commission_percent(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("La commission Pro doit être comprise entre 0 et 100 %.")
        return value

    def validate_mentor_commission_percent(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("La commission mentor doit être comprise entre 0 et 100 %.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        for field in (
            "instructor_pro_monthly_eur", "employer_single_post_eur",
            "employer_pro_monthly_eur", "employer_business_monthly_eur",
        ):
            if field in attrs and attrs[field] < 0:
                raise serializers.ValidationError({field: "Le montant ne peut pas être négatif."})
        return attrs

    def validate_certificate_default_threshold_percent(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("Le seuil doit être compris entre 0 et 100 %.")
        return value

    def validate_certificate_default_attendance_percent(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("Le seuil de présence doit être compris entre 0 et 100 %.")
        return value

    def validate_minimum_payout_amount(self, value):
        if value < 0:
            raise serializers.ValidationError("Le montant minimum ne peut pas être négatif.")
        return value

    def validate_whatsapp_live_reminder_minutes(self, value):
        if value < 5 or value > 1440:
            raise serializers.ValidationError("Le rappel live doit être compris entre 5 et 1440 minutes.")
        return value

    def validate_whatsapp_inactivity_days(self, value):
        if value < 2 or value > 90:
            raise serializers.ValidationError("Le délai d'inactivité doit être compris entre 2 et 90 jours.")
        return value

class InstructorApplicationSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_email = serializers.EmailField(source="user.email", read_only=True)
    reviewed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = InstructorApplication
        fields = [
            "id", "user", "user_name", "user_email", "domain", "years_experience",
            "headline", "message", "status", "review_note", "reviewed_by",
            "reviewed_by_name", "reviewed_at", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "user", "user_name", "user_email", "status", "review_note",
            "reviewed_by", "reviewed_by_name", "reviewed_at", "created_at", "updated_at",
        ]

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def get_reviewed_by_name(self, obj):
        if not obj.reviewed_by:
            return ""
        return obj.reviewed_by.get_full_name() or obj.reviewed_by.username


class InstructorApplicationAdminSerializer(InstructorApplicationSerializer):
    class Meta(InstructorApplicationSerializer.Meta):
        read_only_fields = [
            "id", "user", "user_name", "user_email", "reviewed_by",
            "reviewed_by_name", "reviewed_at", "created_at", "updated_at",
        ]

