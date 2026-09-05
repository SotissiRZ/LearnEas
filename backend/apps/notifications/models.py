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
    whatsapp_recruitment_enabled = models.BooleanField(default=True)
    whatsapp_consent_at = models.DateTimeField(null=True, blank=True)

    # Centre interne KalanPro. Il reste activé par défaut afin que les événements
    # importants soient visibles même sans fournisseur externe configuré.
    in_app_enabled = models.BooleanField(default=True)

    # Email transactionnel via Resend. Les messages purement transactionnels sont
    # activés par défaut ; la relance d'inactivité reste opt-in pour éviter toute
    # assimilation à de la prospection.
    email_enabled = models.BooleanField(default=True)
    email_payment_enabled = models.BooleanField(default=True)
    email_live_enabled = models.BooleanField(default=True)
    email_inactivity_enabled = models.BooleanField(default=False)
    email_certificate_enabled = models.BooleanField(default=True)
    email_recruitment_enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Préférences notifications · {self.user}"


class WhatsAppDelivery(models.Model):
    class EventType(models.TextChoices):
        PAYMENT = "payment", "Paiement confirmé"
        LIVE = "live", "Rappel de live"
        INACTIVITY = "inactivity", "Relance d'inactivité"
        CERTIFICATE = "certificate", "Certificat disponible"
        RECRUITMENT = "recruitment", "Recrutement"
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


class EmailDelivery(models.Model):
    class EventType(models.TextChoices):
        WELCOME = "welcome", "Bienvenue"
        PAYMENT = "payment", "Paiement confirmé"
        LIVE = "live", "Rappel de live"
        INACTIVITY = "inactivity", "Relance d'inactivité"
        CERTIFICATE = "certificate", "Certificat disponible"
        RECRUITMENT = "recruitment", "Recrutement"
        PASSWORD_RESET = "password_reset", "Réinitialisation du mot de passe"
        SESSION_INVITE = "session_invite", "Invitation à une séance"
        TEST = "test", "Test administrateur"

    class Status(models.TextChoices):
        QUEUED = "queued", "En attente"
        SIMULATED = "simulated", "Simulé"
        SENT = "sent", "Envoyé"
        FAILED = "failed", "Échec"
        SKIPPED = "skipped", "Ignoré"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="email_deliveries",
    )
    recipient = models.EmailField(db_index=True)
    event_type = models.CharField(max_length=30, choices=EventType.choices, db_index=True)
    event_key = models.CharField(max_length=220, unique=True)
    subject = models.CharField(max_length=255)
    template_key = models.CharField(max_length=80, default="transactional")
    template_context = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    provider_message_id = models.CharField(max_length=180, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED, db_index=True)
    provider_response = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"], name="notif_email_status_created_idx"),
            models.Index(fields=["event_type", "created_at"], name="notif_email_event_created_idx"),
        ]

    def __str__(self):
        return f"Email {self.event_type} → {self.recipient} · {self.status}"


class InAppNotification(models.Model):
    class Category(models.TextChoices):
        SYSTEM = "system", "Système"
        LEARNING = "learning", "Apprentissage"
        PAYMENT = "payment", "Paiement"
        LIVE = "live", "Live"
        MENTORSHIP = "mentorship", "Mentorat"
        RECRUITMENT = "recruitment", "Recrutement"
        CERTIFICATE = "certificate", "Certificat"

    class Priority(models.TextChoices):
        LOW = "low", "Faible"
        NORMAL = "normal", "Normale"
        HIGH = "high", "Haute"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="in_app_notifications"
    )
    event_key = models.CharField(max_length=240, unique=True)
    category = models.CharField(max_length=24, choices=Category.choices, default=Category.SYSTEM, db_index=True)
    event_type = models.CharField(max_length=64, db_index=True)
    title = models.CharField(max_length=180)
    body = models.TextField(blank=True)
    action_url = models.CharField(max_length=500, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    priority = models.CharField(max_length=12, choices=Priority.choices, default=Priority.NORMAL, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["user", "read_at", "-created_at"], name="notif_inapp_user_read_idx"),
            models.Index(fields=["user", "category", "-created_at"], name="notif_inapp_user_cat_idx"),
        ]

    @property
    def is_read(self):
        return self.read_at is not None

    def __str__(self):
        return f"Notification {self.user_id} · {self.title}"
