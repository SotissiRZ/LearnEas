from django.db.models import Q
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.enrollments.models import CourseEnrollment, PDFPurchase
from .models import Category, Course, Section, Lesson, PDFResource, PDFProduct
from .permissions import IsInstructorOrAdmin
from .serializers import (
    CategorySerializer, CourseListSerializer, CourseDetailSerializer, CourseWriteSerializer,
    SectionWriteSerializer, LessonWriteSerializer, PDFResourceWriteSerializer,
    PDFProductListSerializer, PDFProductDetailSerializer, PDFProductWriteSerializer,
)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAdminUser | permissions.IsAuthenticatedOrReadOnly]
    lookup_field = "slug"
    pagination_class = None  # toujours renvoyée en liste complète (utilisée pour les filtres/menus)


def _enrolled_ids(user):
    if not user or not user.is_authenticated:
        return set()
    return set(CourseEnrollment.objects.filter(user=user).values_list("course_id", flat=True))


def _purchased_pdf_ids(user):
    if not user or not user.is_authenticated:
        return set()
    return set(PDFPurchase.objects.filter(user=user).values_list("pdf_product_id", flat=True))


class CourseViewSet(viewsets.ModelViewSet):
    """
    Catalogue de cours (playlists complètes).
    Filtres: ?category=<slug>&level=&language=&is_free=&search=&ordering=
    """
    queryset = Course.objects.select_related("instructor", "category").filter(published=True)
    permission_classes = [IsInstructorOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["level", "language", "is_free", "category__slug", "instructor__id"]
    search_fields = ["title", "subtitle", "description"]
    ordering_fields = ["created_at", "price", "rating_avg", "students_count", "total_duration_minutes"]
    lookup_field = "slug"

    def get_queryset(self):
        qs = Course.objects.select_related("instructor", "category").prefetch_related(
            "sections__lessons", "pdf_resources"
        )
        user = self.request.user
        if user.is_authenticated and user.role in ("instructor", "admin"):
            if self.action in ("my_courses",):
                return qs.filter(instructor=user)
            if user.role == "admin":
                return qs
            return qs.filter(Q(published=True) | Q(instructor=user))
        return qs.filter(published=True)

    def get_serializer_class(self):
        if self.action == "list":
            return CourseListSerializer
        if self.action in ("create", "update", "partial_update"):
            return CourseWriteSerializer
        return CourseDetailSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["enrolled_course_ids"] = _enrolled_ids(self.request.user)
        return ctx

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def my_courses(self, request):
        """Cours créés par l'instructeur connecté."""
        qs = self.get_queryset().filter(instructor=request.user)
        page = self.paginate_queryset(qs)
        serializer = CourseListSerializer(page or qs, many=True, context=self.get_serializer_context())
        return self.get_paginated_response(serializer.data) if page is not None else Response(serializer.data)

    @action(detail=False, methods=["get"])
    def featured(self, request):
        qs = self.get_queryset().filter(published=True, featured=True)[:8]
        serializer = CourseListSerializer(qs, many=True, context=self.get_serializer_context())
        return Response(serializer.data)


class SectionViewSet(viewsets.ModelViewSet):
    queryset = Section.objects.all()
    serializer_class = SectionWriteSerializer
    permission_classes = [IsInstructorOrAdmin]
    filterset_fields = ["course"]


class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.all()
    serializer_class = LessonWriteSerializer
    permission_classes = [IsInstructorOrAdmin]
    filterset_fields = ["section"]


class PDFResourceViewSet(viewsets.ModelViewSet):
    queryset = PDFResource.objects.all()
    serializer_class = PDFResourceWriteSerializer
    permission_classes = [IsInstructorOrAdmin]
    filterset_fields = ["course"]


class PDFProductViewSet(viewsets.ModelViewSet):
    """Catalogue de PDF vendus SEULS (indépendamment des cours vidéo)."""
    permission_classes = [IsInstructorOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["level", "language", "is_free", "category__slug", "instructor__id"]
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "price", "rating_avg", "downloads_count"]
    lookup_field = "slug"

    def get_queryset(self):
        qs = PDFProduct.objects.select_related("instructor", "category")
        user = self.request.user
        if user.is_authenticated and user.role == "admin":
            return qs
        if user.is_authenticated and user.role == "instructor" and self.action == "my_pdfs":
            return qs.filter(instructor=user)
        return qs.filter(published=True)

    def get_serializer_class(self):
        if self.action == "list":
            return PDFProductListSerializer
        if self.action in ("create", "update", "partial_update"):
            return PDFProductWriteSerializer
        return PDFProductDetailSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["purchased_pdf_ids"] = _purchased_pdf_ids(self.request.user)
        return ctx

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def my_pdfs(self, request):
        qs = self.get_queryset().filter(instructor=request.user)
        page = self.paginate_queryset(qs)
        serializer = PDFProductListSerializer(page or qs, many=True, context=self.get_serializer_context())
        return self.get_paginated_response(serializer.data) if page is not None else Response(serializer.data)
