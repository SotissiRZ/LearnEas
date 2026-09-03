import re
from django.utils import timezone
from rest_framework import serializers
from .models import NotificationPreference, WhatsAppDelivery


_E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")


def normalize_whatsapp_phone(value: str) -> str:
    value = str(value or "").strip()
    value = re.sub(r"[\s().-]+", "", value)
    if value.startswith("00"):
        value = "+" + value[2:]
    if value and not value.startswith("+"):
        raise serializers.ValidationError("Utilisez le format international, par ex. +221771234567.")
    if value and not _E164_RE.match(value):
        raise serializers.ValidationError("Numéro WhatsApp invalide. Utilisez le format E.164, par ex. +2250700000000.")
    return value


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            "whatsapp_phone", "whatsapp_opt_in", "whatsapp_payment_enabled",
            "whatsapp_live_enabled", "whatsapp_inactivity_enabled",
            "whatsapp_certificate_enabled", "whatsapp_consent_at", "updated_at",
        ]
        read_only_fields = ["whatsapp_consent_at", "updated_at"]

    def validate_whatsapp_phone(self, value):
        return normalize_whatsapp_phone(value)

    def validate(self, attrs):
        current_phone = getattr(self.instance, "whatsapp_phone", "") if self.instance else ""
        phone = attrs.get("whatsapp_phone", current_phone)
        opt_in = attrs.get("whatsapp_opt_in", getattr(self.instance, "whatsapp_opt_in", False) if self.instance else False)
        if opt_in and not phone:
            raise serializers.ValidationError({"whatsapp_phone": "Ajoutez un numéro avant d'activer WhatsApp."})
        return attrs

    def update(self, instance, validated_data):
        was_opted_in = instance.whatsapp_opt_in
        instance = super().update(instance, validated_data)
        if instance.whatsapp_opt_in and (not was_opted_in or not instance.whatsapp_consent_at):
            instance.whatsapp_consent_at = timezone.now()
            instance.save(update_fields=["whatsapp_consent_at"])
        elif not instance.whatsapp_opt_in and instance.whatsapp_consent_at:
            instance.whatsapp_consent_at = None
            instance.save(update_fields=["whatsapp_consent_at"])
        return instance


class WhatsAppDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = WhatsAppDelivery
        fields = [
            "id", "recipient", "event_type", "event_key", "template_name", "language_code",
            "status", "provider_message_id", "error", "created_at", "sent_at", "delivered_at", "read_at",
        ]
        read_only_fields = fields
