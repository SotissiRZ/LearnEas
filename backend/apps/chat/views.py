from django.db.models import Q
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import ChatMessage
from .serializers import ChatMessageSerializer


class ChatMessageViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "head", "options"]
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        other_id = self.request.query_params.get("with")
        qs = ChatMessage.objects.filter(Q(sender=user) | Q(recipient=user))
        if other_id:
            qs = qs.filter(Q(sender_id=other_id) | Q(recipient_id=other_id))
        return qs


    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        msg = self.get_object()
        if msg.recipient_id != request.user.id:
            return Response({"detail": "Seul le destinataire peut marquer ce message comme lu."}, status=status.HTTP_403_FORBIDDEN)
        if not msg.is_read:
            msg.is_read = True
            msg.save(update_fields=["is_read"])
        return Response(self.get_serializer(msg).data)
