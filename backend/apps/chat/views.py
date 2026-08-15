from django.db.models import Q
from rest_framework import viewsets, permissions
from .models import ChatMessage
from .serializers import ChatMessageSerializer


class ChatMessageViewSet(viewsets.ModelViewSet):
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        other_id = self.request.query_params.get("with")
        qs = ChatMessage.objects.filter(Q(sender=user) | Q(recipient=user))
        if other_id:
            qs = qs.filter(Q(sender_id=other_id) | Q(recipient_id=other_id))
        return qs
