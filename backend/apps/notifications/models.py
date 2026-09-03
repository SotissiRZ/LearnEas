from django.conf import settings
from django.db import models


class NotificationPreference(models.Model):
    """Consentement et préférences de notifications transactionnelles de l'utilisateur."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )
    whatsapp_phone = models.CharField(
        max_length=32,
        blank=True,
        help_text="Numéro WhatsApp au format international E.164, ex. +221771234567.",
    )
    whatsapp_opt_in = models.BooleanField(default=False)
    whatsapp_payment_enabled = models.BooleanField(default=True)
    whatsapp_live_enabled = models.BooleanField(default=True)
    whatsapp_inactivity_enabled = models.BooleanField(default=True)
    whatsapp_certificate_enabled = models.BooleanField(default=True)
    whatsapp_consent_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Préférences notifications · {self.user}"


class WhatsAppDelivery(models.Model):
    class EventType(models.TextChoices):
        PAYMENT = "payment", "Paiement confirmé"
        LIVE = "live", "Rappel de live"
        INACTIVITY = "inactivity", "Relance d'inactivité"
        CERTIFICATE = "certificate", "Certificat disponible"
        TEST = "test", "Test administrateur"

    class Status(models.TextChoices):
        QUEUED = "queued", "En attente"
        SIMULATED = "simulated", "Simulé"
        SENT = "sent", "Envoyé"
        DELIVERED = "delivered", "Livré"
        READ = "read", "Lu"
        FAILED = "failed", "Échec"
        SKIPPED = "skipped", "Ignoré"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="whatsapp_deliveries",
    )
    recipient = models.CharField(max_length=32)
    event_type = models.CharField(max_length=20, choices=EventType.choices, db_index=True)
    event_key = models.CharField(max_length=180, unique=True)
    template_name = models.CharField(max_length=120)
    language_code = models.CharField(max_length=16, default="fr")
    variables = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    provider_message_id = models.CharField(max_length=180, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED, db_index=True)
    provider_response = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"], name="notif_wa_status_created_idx"),
            models.Index(fields=["event_type", "created_at"], name="notif_wa_event_created_idx"),
        ]

    def __str__(self):
        return f"WhatsApp {self.event_type} → {self.recipient} · {self.status}"
