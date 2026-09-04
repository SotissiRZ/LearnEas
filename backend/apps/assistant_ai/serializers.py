from rest_framework import serializers
from .models import AIConversation, AIMessage, AISettings, AIAttachment
from .attachments import serialize_attachment


class AIMessageSerializer(serializers.ModelSerializer):
    attachments = serializers.SerializerMethodField()

    def get_attachments(self, obj):
        return [serialize_attachment(row) for row in obj.attachments.all()]

    class Meta:
        model = AIMessage
        fields = ["id", "role", "content", "sources", "actions", "attachments", "provider", "model", "feedback", "feedback_comment", "feedback_at", "created_at"]


class AIConversationListSerializer(serializers.ModelSerializer):
    messages_count = serializers.SerializerMethodField()

    def get_messages_count(self, obj):
        value = getattr(obj, "messages_count", None)
        return int(value if value is not None else obj.messages.count())

    class Meta:
        model = AIConversation
        fields = ["id", "title", "context_preview", "archived", "created_at", "updated_at", "messages_count"]


class AIConversationDetailSerializer(AIConversationListSerializer):
    messages = AIMessageSerializer(many=True, read_only=True)
    class Meta(AIConversationListSerializer.Meta):
        fields = AIConversationListSerializer.Meta.fields + ["messages"]


class AISettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AISettings
        fields = [
            "enabled", "rag_enabled", "history_enabled", "tools_enabled", "attachments_enabled", "student_enabled", "instructor_enabled", "admin_enabled",
            "default_model", "student_monthly_limit", "instructor_monthly_limit", "admin_monthly_limit",
            "max_history_messages", "max_context_chunks", "max_attachment_mb", "max_attachments_per_message", "max_attachment_text_chars", "max_output_tokens", "temperature", "input_cost_per_million_eur", "output_cost_per_million_eur", "custom_system_prompt", "updated_at",
        ]
