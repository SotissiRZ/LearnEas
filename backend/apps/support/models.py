import uuid

from django.conf import settings
from django.db import models


def ticket_reference():
    return f"KP-{uuid.uuid4().hex[:10].upper()}"


class SupportTicket(models.Model):
    class Category(models.TextChoices):
        ACCOUNT = "account", "Compte et connexion"
        PAYMENT = "payment", "Paiement et remboursement"
        LEARNING = "learning", "Cours et apprentissage"
        TECHNICAL = "technical", "Problème technique"
        RECRUITMENT = "recruitment", "Emploi et recrutement"
        SAFETY = "safety", "Sécurité et modération"
        OTHER = "other", "Autre"

    class Priority(models.TextChoices):
        LOW = "low", "Faible"
        NORMAL = "normal", "Normale"
        HIGH = "high", "Haute"
        URGENT = "urgent", "Urgente"

    class Status(models.TextChoices):
        OPEN = "open", "Ouvert"
        IN_PROGRESS = "in_progress", "En cours"
        WAITING_USER = "waiting_user", "En attente utilisateur"
        RESOLVED = "resolved", "Résolu"
        CLOSED = "closed", "Fermé"

    reference = models.CharField(max_length=20, unique=True, default=ticket_reference, editable=False)
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="support_tickets")
    subject = models.CharField(max_length=180)
    category = models.CharField(max_length=24, choices=Category.choices, default=Category.OTHER, db_index=True)
    priority = models.CharField(max_length=12, choices=Priority.choices, default=Priority.NORMAL, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN, db_index=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assigned_support_tickets", limit_choices_to={"role": "admin"},
    )
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_message_at", "-created_at", "-id"]
        indexes = [
            models.Index(fields=["requester", "status", "-updated_at"], name="support_ticket_user_status_idx"),
            models.Index(fields=["status", "priority", "-updated_at"], name="support_ticket_queue_idx"),
        ]

    def __str__(self):
        return f"{self.reference} · {self.subject}"


class SupportMessage(models.Model):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="support_messages")
    body = models.TextField()
    is_staff_reply = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["ticket", "created_at"], name="support_message_ticket_idx")]

    def __str__(self):
        return f"Message {self.ticket.reference} · {self.created_at:%Y-%m-%d %H:%M}"


class ModerationReport(models.Model):
    class TargetType(models.TextChoices):
        USER = "user", "Utilisateur"
        REVIEW = "review", "Avis"
        COMMENT = "comment", "Commentaire"
        COURSE = "course", "Cours"
        PDF = "pdf", "PDF"
        FORMATION = "formation", "Formation"
        OPPORTUNITY = "opportunity", "Opportunité"
        MESSAGE = "message", "Message"
        OTHER = "other", "Autre"

    class Reason(models.TextChoices):
        HARASSMENT = "harassment", "Harcèlement ou menace"
        SPAM = "spam", "Spam"
        FRAUD = "fraud", "Fraude ou arnaque"
        IMPERSONATION = "impersonation", "Usurpation d'identité"
        INAPPROPRIATE = "inappropriate", "Contenu inapproprié"
        ILLEGAL = "illegal", "Contenu potentiellement illégal"
        COPYRIGHT = "copyright", "Droits d'auteur"
        MISINFORMATION = "misinformation", "Information trompeuse"
        OTHER = "other", "Autre"

    class Status(models.TextChoices):
        PENDING = "pending", "À examiner"
        REVIEWING = "reviewing", "En cours d'examen"
        ACTIONED = "actioned", "Action effectuée"
        DISMISSED = "dismissed", "Classé sans suite"

    class Severity(models.TextChoices):
        LOW = "low", "Faible"
        MEDIUM = "medium", "Moyenne"
        HIGH = "high", "Élevée"
        CRITICAL = "critical", "Critique"

    class Action(models.TextChoices):
        NONE = "none", "Aucune"
        WARNING = "warning", "Avertissement"
        CONTENT_REMOVED = "content_removed", "Contenu retiré"
        USER_RESTRICTED = "user_restricted", "Utilisateur restreint"
        ESCALATED = "escalated", "Escalade"

    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="moderation_reports")
    target_type = models.CharField(max_length=24, choices=TargetType.choices, db_index=True)
    target_id = models.CharField(max_length=120, blank=True, db_index=True)
    target_label = models.CharField(max_length=255, blank=True)
    target_url = models.CharField(max_length=500, blank=True)
    reason = models.CharField(max_length=24, choices=Reason.choices, db_index=True)
    details = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True)
    severity = models.CharField(max_length=12, choices=Severity.choices, default=Severity.MEDIUM, db_index=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assigned_moderation_reports", limit_choices_to={"role": "admin"},
    )
    action_taken = models.CharField(max_length=24, choices=Action.choices, default=Action.NONE)
    resolution_note = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["status", "severity", "-created_at"], name="moderation_queue_idx"),
            models.Index(fields=["target_type", "target_id"], name="moderation_target_idx"),
        ]

    def __str__(self):
        return f"Signalement #{self.pk or '-'} · {self.target_type}:{self.target_id or '-'}"


class ModerationActionLog(models.Model):
    report = models.ForeignKey(ModerationReport, on_delete=models.CASCADE, related_name="action_logs")
    moderator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="moderation_actions")
    previous_status = models.CharField(max_length=16, blank=True)
    new_status = models.CharField(max_length=16, blank=True)
    action = models.CharField(max_length=24, choices=ModerationReport.Action.choices, default=ModerationReport.Action.NONE)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"Action modération #{self.report_id}"
