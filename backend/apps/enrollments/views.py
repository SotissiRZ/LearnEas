from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.catalog.models import Lesson, Course, PDFProduct
from .models import CourseEnrollment, LessonProgress, PDFPurchase, Wishlist
from .serializers import (
    CourseEnrollmentSerializer, LessonProgressSerializer, PDFPurchaseSerializer, WishlistSerializer,
)


class CourseEnrollmentViewSet(viewsets.ReadOnlyModelViewSet):
    """Liste 'Mes cours' de l'utilisateur connecté + suivi de progression."""
    serializer_class = CourseEnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CourseEnrollment.objects.filter(user=self.request.user).select_related("course")

    @action(detail=True, methods=["post"])
    def mark_lesson_complete(self, request, pk=None):
        enrollment = self.get_object()
        lesson_id = request.data.get("lesson_id")
        lesson = get_object_or_404(Lesson, id=lesson_id, section__course=enrollment.course)

        progress, _ = LessonProgress.objects.get_or_create(enrollment=enrollment, lesson=lesson)
        progress.completed = True
        progress.watched_seconds = request.data.get("watched_seconds", progress.watched_seconds)
        progress.save()

        total = Lesson.objects.filter(section__course=enrollment.course).count()
        done = LessonProgress.objects.filter(enrollment=enrollment, completed=True).count()
        enrollment.progress_percent = int((done / total) * 100) if total else 0
        enrollment.last_accessed_lesson = lesson
        if enrollment.progress_percent >= 100 and not enrollment.completed:
            enrollment.completed = True
            enrollment.completed_at = timezone.now()
            enrollment.certificate_issued = True
        enrollment.save()

        return Response(CourseEnrollmentSerializer(enrollment).data)

    @action(detail=True, methods=["get"])
    def certificate(self, request, pk=None):
        enrollment = self.get_object()
        if not enrollment.certificate_issued:
            return Response({"detail": "Certificat non disponible : cours non terminé."}, status=400)
        return Response({
            "student_name": request.user.get_full_name() or request.user.username,
            "course_title": enrollment.course.title,
            "instructor_name": enrollment.course.instructor.get_full_name() or enrollment.course.instructor.username,
            "completed_at": enrollment.completed_at,
            "total_hours": enrollment.course.total_hours,
            "certificate_id": f"LE-CERT-{enrollment.id:06d}",
        })


class WishlistViewSet(viewsets.ModelViewSet):
    serializer_class = WishlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        course_id = request.data.get("course")
        pdf_id = request.data.get("pdf_product")
        obj, created = Wishlist.objects.get_or_create(
            user=request.user,
            course_id=course_id or None,
            pdf_product_id=pdf_id or None,
        )
        return Response(WishlistSerializer(obj).data, status=status.HTTP_201_CREATED if created else 200)


class MyPDFsViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PDFPurchaseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PDFPurchase.objects.filter(user=self.request.user).select_related("pdf_product")
