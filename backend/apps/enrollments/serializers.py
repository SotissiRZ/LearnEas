from rest_framework import serializers
from apps.catalog.serializers import CourseListSerializer, PDFProductListSerializer
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


class PDFPurchaseSerializer(serializers.ModelSerializer):
    pdf_product = PDFProductListSerializer(read_only=True)

    class Meta:
        model = PDFPurchase
        fields = ["id", "pdf_product", "purchased_at"]


class WishlistSerializer(serializers.ModelSerializer):
    course = CourseListSerializer(read_only=True)
    pdf_product = PDFProductListSerializer(read_only=True)

    class Meta:
        model = Wishlist
        fields = ["id", "course", "pdf_product", "added_at"]
