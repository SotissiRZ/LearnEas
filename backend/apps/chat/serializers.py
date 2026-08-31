from rest_framework import serializers
from .models import ChatMessage


class ChatMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    recipient_name = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = [
            "id", "sender", "sender_name", "recipient", "recipient_name",
            "content", "is_read", "created_at",
        ]
        read_only_fields = ["sender", "is_read"]

    def get_sender_name(self, obj):
        return obj.sender.get_full_name() or obj.sender.username

    def get_recipient_name(self, obj):
        return obj.recipient.get_full_name() or obj.recipient.username

    def validate(self, attrs):
        sender = self.context["request"].user
        recipient = attrs.get("recipient")
        content = str(attrs.get("content", "") or "").strip()
        if not recipient or not recipient.is_active:
            raise serializers.ValidationError({"recipient": "Destinataire invalide ou inactif."})
        if recipient.id == sender.id:
            raise serializers.ValidationError({"recipient": "Vous ne pouvez pas vous envoyer un message à vous-même."})
        if not content:
            raise serializers.ValidationError({"content": "Le message ne peut pas être vide."})
        if len(content) > 5000:
            raise serializers.ValidationError({"content": "Le message est limité à 5 000 caractères."})
        attrs["content"] = content
        return attrs

    def create(self, validated_data):
        validated_data["sender"] = self.context["request"].user
        return super().create(validated_data)
