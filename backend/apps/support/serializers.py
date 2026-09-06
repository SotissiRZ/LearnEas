from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.accounts.models import User
from .models import SupportTicket, SupportMessage, ModerationReport, ModerationActionLog


class SupportMessageSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    author_role = serializers.CharField(source="author.role", read_only=True, default="")

    class Meta:
        model = SupportMessage
        fields = ["id", "author", "author_name", "author_role", "body", "is_staff_reply", "created_at"]
        read_only_fields = ["author", "is_staff_reply", "created_at"]

    def get_author_name(self, obj):
        if not obj.author:
            return "Support KalanPro" if obj.is_staff_reply else "Utilisateur supprimé"
        return obj.author.get_full_name() or obj.author.username or obj.author.email


class SupportTicketSerializer(serializers.ModelSerializer):
    requester_name = serializers.SerializerMethodField()
    requester_email = serializers.EmailField(source="requester.email", read_only=True)
    assigned_to_name = serializers.SerializerMethodField()
    last_message_preview = serializers.SerializerMethodField()
    message_count = serializers.IntegerField(read_only=True, default=0)
    initial_message = serializers.CharField(write_only=True, required=False, allow_blank=False, max_length=6000)

    class Meta:
        model = SupportTicket
        fields = [
            "id", "reference", "requester", "requester_name", "requester_email", "subject", "category",
            "priority", "status", "assigned_to", "assigned_to_name", "last_message_at", "last_message_preview",
            "message_count", "resolved_at", "closed_at", "created_at", "updated_at", "initial_message",
        ]
        read_only_fields = ["reference", "requester", "last_message_at", "resolved_at", "closed_at", "created_at", "updated_at"]

    def get_requester_name(self, obj):
        return obj.requester.get_full_name() or obj.requester.username or obj.requester.email

    def get_assigned_to_name(self, obj):
        if not obj.assigned_to:
            return ""
        return obj.assigned_to.get_full_name() or obj.assigned_to.username or obj.assigned_to.email

    def get_last_message_preview(self, obj):
        message = getattr(obj, "latest_message", None)
        if message is None:
            message = obj.messages.order_by("-created_at", "-id").only("body").first()
        return (message.body[:180] if message else "")

    def validate_subject(self, value):
        value = str(value or "").strip()
        if len(value) < 5:
            raise serializers.ValidationError("Le sujet doit contenir au moins 5 caractères.")
        return value

    def validate_priority(self, value):
        request = self.context.get("request")
        if request and getattr(request.user, "role", "") != "admin" and value == SupportTicket.Priority.URGENT:
            raise serializers.ValidationError("La priorité urgente est attribuée par le support.")
        return value

    def validate_assigned_to(self, value):
        if value and value.role != User.Role.ADMIN:
            raise serializers.ValidationError("Le ticket ne peut être assigné qu'à un administrateur.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        initial_message = str(validated_data.pop("initial_message", "") or "").strip()
        if not initial_message:
            raise serializers.ValidationError({"initial_message": "Décrivez le problème rencontré."})
        request = self.context["request"]
        # Le demandeur ne peut ni s'assigner le ticket ni choisir un état terminal à la création.
        validated_data.pop("assigned_to", None)
        validated_data["status"] = SupportTicket.Status.OPEN
        now = timezone.now()
        ticket = SupportTicket.objects.create(requester=request.user, last_message_at=now, **validated_data)
        SupportMessage.objects.create(ticket=ticket, author=request.user, body=initial_message, is_staff_reply=False)
        return ticket


class ModerationActionLogSerializer(serializers.ModelSerializer):
    moderator_name = serializers.SerializerMethodField()

    class Meta:
        model = ModerationActionLog
        fields = ["id", "moderator", "moderator_name", "previous_status", "new_status", "action", "note", "created_at"]
        read_only_fields = fields

    def get_moderator_name(self, obj):
        if not obj.moderator:
            return "Administrateur supprimé"
        return obj.moderator.get_full_name() or obj.moderator.username or obj.moderator.email


class ModerationReportSerializer(serializers.ModelSerializer):
    reporter_name = serializers.SerializerMethodField()
    reporter_email = serializers.EmailField(source="reporter.email", read_only=True, default="")
    assigned_to_name = serializers.SerializerMethodField()
    action_logs = ModerationActionLogSerializer(many=True, read_only=True)

    class Meta:
        model = ModerationReport
        fields = [
            "id", "reporter", "reporter_name", "reporter_email", "target_type", "target_id", "target_label",
            "target_url", "reason", "details", "status", "severity", "assigned_to", "assigned_to_name",
            "action_taken", "resolution_note", "resolved_at", "created_at", "updated_at", "action_logs",
        ]
        read_only_fields = [
            "reporter", "status", "severity", "assigned_to", "action_taken", "resolution_note",
            "resolved_at", "created_at", "updated_at", "action_logs",
        ]

    def get_reporter_name(self, obj):
        if not obj.reporter:
            return "Utilisateur supprimé"
        return obj.reporter.get_full_name() or obj.reporter.username or obj.reporter.email

    def get_assigned_to_name(self, obj):
        if not obj.assigned_to:
            return ""
        return obj.assigned_to.get_full_name() or obj.assigned_to.username or obj.assigned_to.email

    def validate(self, attrs):
        if "target_id" in attrs:
            attrs["target_id"] = str(attrs.get("target_id", "") or "").strip()[:120]
        if "target_label" in attrs:
            attrs["target_label"] = str(attrs.get("target_label", "") or "").strip()[:255]
        if "target_url" in attrs:
            attrs["target_url"] = str(attrs.get("target_url", "") or "").strip()[:500]
        if "details" in attrs:
            details = str(attrs.get("details", "") or "").strip()
            if len(details) > 6000:
                raise serializers.ValidationError({"details": "Le détail est limité à 6 000 caractères."})
            attrs["details"] = details

        request = self.context.get("request")
        if request and request.user.is_authenticated:
            duplicate_qs = ModerationReport.objects.none()
            target_id = attrs.get("target_id", getattr(self.instance, "target_id", ""))
            target_type = attrs.get("target_type", getattr(self.instance, "target_type", ""))
            if target_id:
                duplicate_qs = ModerationReport.objects.filter(
                    reporter=request.user,
                    target_type=target_type,
                    target_id=target_id,
                    status__in=[ModerationReport.Status.PENDING, ModerationReport.Status.REVIEWING],
                )
                if self.instance is not None:
                    duplicate_qs = duplicate_qs.exclude(pk=self.instance.pk)
            if duplicate_qs.exists():
                raise serializers.ValidationError("Un signalement actif existe déjà pour cet élément.")
        return attrs

    def validate_target_url(self, value):
        value = str(value or "").strip()
        if not value:
            return ""
        if value.startswith("/") and not value.startswith("//"):
            return value[:500]
        if value.startswith("https://") or value.startswith("http://"):
            return value[:500]
        raise serializers.ValidationError("Utilisez une URL relative KalanPro ou une URL http(s).")

    def create(self, validated_data):
        return ModerationReport.objects.create(reporter=self.context["request"].user, **validated_data)


class ModerationReportAdminSerializer(ModerationReportSerializer):
    class Meta(ModerationReportSerializer.Meta):
        read_only_fields = ["reporter", "resolved_at", "created_at", "updated_at", "action_logs"]

    def validate_assigned_to(self, value):
        if value and value.role != User.Role.ADMIN:
            raise serializers.ValidationError("Un signalement ne peut être assigné qu'à un administrateur.")
        return value
