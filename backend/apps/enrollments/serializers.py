from rest_framework import serializers
from apps.catalog.serializers import CourseListSerializer, PDFProductListSerializer
from apps.common.fields import RelativeFileField, ProtectedFileField
from .models import CourseEnrollment, LessonProgress, LessonNote, PDFPurchase, Wishlist


class LessonProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonProgress
        fields = ["id", "enrollment", "lesson", "completed", "watched_seconds", "last_position_seconds", "updated_at"]
        read_only_fields = ["id", "enrollment", "updated_at"]


class CourseEnrollmentSerializer(serializers.ModelSerializer):
    course = CourseListSerializer(read_only=True)
    lesson_progress = LessonProgressSerializer(many=True, read_only=True)

    class Meta:
        model = CourseEnrollment
        fields = [
            "id", "course", "purchased_at", "progress_percent",
            "completed", "certificate_issued", "last_accessed_lesson", "lesson_progress",
        ]


class LessonNoteSerializer(serializers.ModelSerializer):
    lesson_title = serializers.CharField(source="lesson.title", read_only=True)
    section_title = serializers.CharField(source="lesson.section.title", read_only=True)
    course_id = serializers.IntegerField(source="lesson.section.course_id", read_only=True)

    class Meta:
        model = LessonNote
        fields = [
            "id", "lesson", "lesson_title", "section_title", "course_id",
            "timestamp_seconds", "content", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "lesson_title", "section_title", "course_id", "created_at", "updated_at"]

    def validate_content(self, value):
        value = str(value or "").strip()
        if not value:
            raise serializers.ValidationError("La note ne peut pas être vide.")
        if len(value) > 5000:
            raise serializers.ValidationError("La note est limitée à 5 000 caractères.")
        return value


class PurchasedPDFProductSerializer(PDFProductListSerializer):
    # Cet endpoint est déjà filtré par l'achat de l'utilisateur authentifié : le fichier
    # complet peut donc être renvoyé ici sans dépendre du serializer public du catalogue.
    file = ProtectedFileField(read_only=True)

    class Meta(PDFProductListSerializer.Meta):
        fields = PDFProductListSerializer.Meta.fields + ["file"]


class PDFPurchaseSerializer(serializers.ModelSerializer):
    pdf_product = PurchasedPDFProductSerializer(read_only=True)

    class Meta:
        model = PDFPurchase
        fields = ["id", "pdf_product", "purchased_at"]


class WishlistSerializer(serializers.ModelSerializer):
    course = CourseListSerializer(read_only=True)
    pdf_product = PDFProductListSerializer(read_only=True)

    class Meta:
        model = Wishlist
        fields = ["id", "course", "pdf_product", "added_at"]


from .models import Certificate, CertificateEvent


class CertificateEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = CertificateEvent
        fields = ["id", "event_type", "actor_name", "details", "created_at"]
        read_only_fields = fields

    def get_actor_name(self, obj):
        if not obj.actor:
            return "Système KalanPro"
        return obj.actor.get_full_name() or obj.actor.username


class CertificateSerializer(serializers.ModelSerializer):
    effective_status = serializers.ReadOnlyField()
    verification_url = serializers.SerializerMethodField()
    qr_url = serializers.SerializerMethodField()
    replacement_verification_url = serializers.SerializerMethodField()
    supersedes_certificate_number = serializers.CharField(source="supersedes.certificate_number", read_only=True, allow_null=True)
    events = CertificateEventSerializer(many=True, read_only=True)

    class Meta:
        model = Certificate
        fields = [
            "id", "certificate_number", "verification_code", "verification_url", "qr_url",
            "status", "effective_status", "issued_at", "expires_at", "revoked_at",
            "revocation_reason", "achievement_percent", "student_name", "content_type",
            "content_title", "instructor_name", "title", "subtitle", "description",
            "signatory_name", "signatory_title", "accent_color", "duration_minutes",
            "completed_at", "display_options", "metadata", "user", "issued_by",
            "course_enrollment", "formation_enrollment", "issuer_name", "issuer_country",
            "skills_snapshot", "projects_snapshot", "credential_digest", "schema_version",
            "supersedes_certificate_number", "replacement_verification_url", "events",
        ]
        read_only_fields = fields

    def _public_url(self, obj):
        from django.conf import settings
        return f"{settings.FRONTEND_URL.rstrip('/')}/certificates/verify/{obj.verification_code}"

    def get_verification_url(self, obj):
        return self._public_url(obj)

    def get_qr_url(self, obj):
        from django.urls import reverse
        request = self.context.get("request")
        path = reverse("certificate-qr", kwargs={"code": obj.verification_code})
        if request:
            return request.build_absolute_uri(path)
        from django.conf import settings
        base = str(getattr(settings, "BACKEND_PUBLIC_URL", "")).rstrip("/")
        return f"{base}{path}" if base else path

    def get_replacement_verification_url(self, obj):
        replacement = obj.replacement_certificates.order_by("-issued_at", "-id").first()
        return self._public_url(replacement) if replacement else None


class PublicCertificateSerializer(serializers.ModelSerializer):
    effective_status = serializers.ReadOnlyField()
    verification_url = serializers.SerializerMethodField()
    qr_url = serializers.SerializerMethodField()
    replacement_verification_url = serializers.SerializerMethodField()
    supersedes_certificate_number = serializers.CharField(source="supersedes.certificate_number", read_only=True, allow_null=True)

    class Meta:
        model = Certificate
        fields = [
            "certificate_number", "verification_code", "verification_url", "qr_url", "effective_status",
            "issued_at", "expires_at", "revoked_at", "achievement_percent", "student_name", "content_type",
            "content_title", "instructor_name", "title", "subtitle", "description",
            "signatory_name", "signatory_title", "accent_color", "duration_minutes",
            "completed_at", "display_options", "issuer_name", "issuer_country", "skills_snapshot",
            "projects_snapshot", "credential_digest", "schema_version", "supersedes_certificate_number",
            "replacement_verification_url",
        ]

    def _public_url(self, obj):
        from django.conf import settings
        return f"{settings.FRONTEND_URL.rstrip('/')}/certificates/verify/{obj.verification_code}"

    def get_verification_url(self, obj):
        return self._public_url(obj)

    def get_qr_url(self, obj):
        from django.urls import reverse
        request = self.context.get("request")
        path = reverse("certificate-qr", kwargs={"code": obj.verification_code})
        if request:
            return request.build_absolute_uri(path)
        from django.conf import settings
        base = str(getattr(settings, "BACKEND_PUBLIC_URL", "")).rstrip("/")
        return f"{base}{path}" if base else path

    def get_replacement_verification_url(self, obj):
        replacement = obj.replacement_certificates.order_by("-issued_at", "-id").first()
        return self._public_url(replacement) if replacement else None

