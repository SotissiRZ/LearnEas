from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import FAQ
from .serializers import FAQSerializer


class IsFaqAuthorOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        if getattr(view, "action", None) == "create":
            return request.user.role in ("admin", "instructor")
        return True

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user.is_authenticated and (request.user.role == "admin" or obj.author_id == request.user.id))


class FAQViewSet(viewsets.ModelViewSet):
    serializer_class = FAQSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsFaqAuthorOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["audience", "author"]
    search_fields = ["question", "answer", "author__email", "author__first_name", "author__last_name"]
    ordering_fields = ["order", "created_at"]
    ordering = ["order", "id"]

    def get_queryset(self):
        qs = FAQ.objects.select_related("author")
        user = self.request.user
        if user.is_authenticated and user.role == "admin":
            return qs
        if user.is_authenticated and user.role == "instructor":
            if self.request.query_params.get("mine"):
                return qs.filter(author=user)
            return qs.filter(audience__in=["all", "instructor"])
        if user.is_authenticated:
            return qs.filter(audience__in=["all", "student"])
        return qs.filter(audience="all")
