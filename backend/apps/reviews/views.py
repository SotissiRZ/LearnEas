from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Avg, Count, Q
from django_filters.rest_framework import DjangoFilterBackend
from .models import Review, LessonComment
from .serializers import ReviewSerializer, LessonCommentSerializer


class IsOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user.is_authenticated and (request.user.role == "admin" or obj.user_id == request.user.id))


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.select_related("user", "course", "pdf_product")
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["course", "pdf_product", "rating"]
    search_fields = ["comment", "user__email", "user__first_name", "user__last_name", "course__title", "pdf_product__title"]
    ordering_fields = ["created_at", "rating"]
    ordering = ["-created_at"]

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated], url_path="mine")
    def mine(self, request):
        if request.user.role not in ("instructor", "admin"):
            return Response({"detail": "Compte instructeur requis."}, status=403)
        qs = self.get_queryset().filter(
            Q(course__instructor=request.user) | Q(pdf_product__instructor=request.user)
        ).distinct()
        qs = self.filter_queryset(qs)
        page = self.paginate_queryset(qs)
        serializer = self.get_serializer(page if page is not None else qs, many=True)
        return self.get_paginated_response(serializer.data) if page is not None else Response(serializer.data)

    def perform_destroy(self, instance):
        course = instance.course
        pdf_product = instance.pdf_product
        instance.delete()
        target = course or pdf_product
        if target:
            qs = Review.objects.filter(course=course) if course else Review.objects.filter(pdf_product=pdf_product)
            stats = qs.aggregate(avg=Avg("rating"), count=Count("id"))
            target.rating_avg = round(stats["avg"] or 0, 2)
            target.rating_count = stats["count"] or 0
            target.save(update_fields=["rating_avg", "rating_count"])


class LessonCommentViewSet(viewsets.ModelViewSet):
    queryset = LessonComment.objects.filter(parent__isnull=True).select_related("user", "lesson")
    serializer_class = LessonCommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["lesson"]
    search_fields = ["content", "user__email", "user__first_name", "user__last_name", "lesson__title"]
    ordering_fields = ["created_at"]
    ordering = ["created_at"]

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated], url_path="mine")
    def mine(self, request):
        if request.user.role not in ("instructor", "admin"):
            return Response({"detail": "Compte instructeur requis."}, status=403)
        qs = LessonComment.objects.filter(
            parent__isnull=True, lesson__section__course__instructor=request.user
        ).select_related("user", "lesson", "lesson__section", "lesson__section__course").prefetch_related("replies__user")
        qs = self.filter_queryset(qs)
        page = self.paginate_queryset(qs)
        serializer = self.get_serializer(page if page is not None else qs, many=True)
        return self.get_paginated_response(serializer.data) if page is not None else Response(serializer.data)
