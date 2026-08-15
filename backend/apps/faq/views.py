from rest_framework import viewsets, permissions
from .models import FAQ
from .serializers import FAQSerializer


class FAQViewSet(viewsets.ModelViewSet):
    serializer_class = FAQSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = FAQ.objects.all()
        user = self.request.user
        if user.is_authenticated and user.role in ("admin", "instructor"):
            if self.request.query_params.get("mine"):
                return qs.filter(author=user)
        return qs.filter(audience__in=["all"]) if not (user.is_authenticated and user.role == "admin") else qs
