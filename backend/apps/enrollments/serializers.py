from rest_framework import serializers
from apps.catalog.serializers import CourseListSerializer, PDFProductListSerializer
from apps.common.fields import RelativeFileField, ProtectedFileField
from .models import CourseEnrollment, LessonProgress, PDFPurchase, Wishlist


class CourseEnrollmentSerializer(serializers.ModelSerializer):
    course = CourseListSerializer(read_only=True)

    class Meta:
        model = CourseEnrollment
        fields = [
            "id", "course", "purchased_at", "progress_percent",
            "completed", "certificate_issued", "last_accessed_lesson",
        ]


class LessonProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonProgress
        fields = ["id", "enrollment", "lesson", "completed", "watched_seconds", "updated_at"]


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


from .models import Certificate


class CertificateSerializer(serializers.ModelSerializer):
    effective_status = serializers.ReadOnlyField()
    verification_url = serializers.SerializerMethodField()

    class Meta:
        model = Certificate
        fields = [
            "id", "certificate_number", "verification_code", "verification_url",
            "status", "effective_status", "issued_at", "expires_at", "revoked_at",
            "revocation_reason", "achievement_percent", "student_name", "content_type",
            "content_title", "instructor_name", "title", "subtitle", "description",
            "signatory_name", "signatory_title", "accent_color", "duration_minutes",
            "completed_at", "display_options", "metadata", "user", "issued_by",
            "course_enrollment", "formation_enrollment",
        ]
        read_only_fields = fields

    def get_verification_url(self, obj):
        from django.conf import settings
        return f"{settings.FRONTEND_URL.rstrip('/')}/certificates/verify/{obj.verification_code}"


class PublicCertificateSerializer(serializers.ModelSerializer):
    effective_status = serializers.ReadOnlyField()
    verification_url = serializers.SerializerMethodField()

    class Meta:
        model = Certificate
        fields = [
            "certificate_number", "verification_code", "verification_url", "effective_status", "issued_at",
            "expires_at", "achievement_percent", "student_name", "content_type",
            "content_title", "instructor_name", "title", "subtitle", "description",
            "signatory_name", "signatory_title", "accent_color", "duration_minutes",
            "completed_at", "display_options",
        ]

    def get_verification_url(self, obj):
        from django.conf import settings
        return f"{settings.FRONTEND_URL.rstrip('/')}/certificates/verify/{obj.verification_code}"
