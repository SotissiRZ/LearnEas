from rest_framework import viewsets, permissions
from .models import Review, LessonComment
from .serializers import ReviewSerializer, LessonCommentSerializer


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.select_related("user")
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filterset_fields = ["course", "pdf_product"]


class LessonCommentViewSet(viewsets.ModelViewSet):
    queryset = LessonComment.objects.filter(parent__isnull=True).select_related("user")
    serializer_class = LessonCommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filterset_fields = ["lesson"]
