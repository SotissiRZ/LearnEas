from django.contrib.auth import get_user_model
from rest_framework import serializers
from apps.common.fields import RelativeImageField
from .models import PlatformSettings, InstructorApplication

User = get_user_model()


class UserPublicSerializer(serializers.ModelSerializer):
    """Utilisé pour afficher un instructeur sur une fiche cours."""
    full_name = serializers.SerializerMethodField()
    courses_count = serializers.SerializerMethodField()
    avatar = RelativeImageField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "full_name", "avatar", "bio", "headline",
            "domain", "years_experience", "courses_count",
        ]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    def get_courses_count(self, obj):
        return obj.courses.filter(published=True).count() if hasattr(obj, "courses") else 0


class UserSerializer(serializers.ModelSerializer):
    avatar = RelativeImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name", "role",
            "avatar", "bio", "country", "headline", "domain",
            "years_experience", "date_joined",
        ]
        read_only_fields = ["id", "role", "date_joined"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "country", "password", "password2"]

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("Un compte existe déjà avec cet email.")
        return email

    def validate_username(self, value):
        username = value.strip()
        if len(username) < 3:
            raise serializers.ValidationError("Doit contenir au moins 3 caractères.")
        if User.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError("Ce nom d'utilisateur est déjà utilisé.")
        return username

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password2": "Les mots de passe ne correspondent pas."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        password = validated_data.pop("password")
        user = User(**validated_data, role=User.Role.STUDENT, is_active=True)
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

    def create(self, validated_data):
        from django.utils.text import slugify
        password = validated_data.pop("password")
        email = validated_data["email"]
        base = slugify(email.split("@")[0]) or "user"
        username = base
        suffix = 1
        while User.objects.filter(username__iexact=username).exists():
            suffix += 1
            username = f"{base}-{suffix}"
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
            "minimum_payout_amount", "updated_at",
        ]
        read_only_fields = ["updated_at"]

    def validate_platform_commission_percent(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("La commission doit être comprise entre 0 et 100 %.")
        return value

    def validate_minimum_payout_amount(self, value):
        if value < 0:
            raise serializers.ValidationError("Le montant minimum ne peut pas être négatif.")
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

