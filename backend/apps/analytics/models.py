from django.conf import settings
from django.db import models


class ProductEvent(models.Model):
    """Événement produit minimisé pour mesurer l'usage sans stocker de contenu saisi.

    Les métriques financières / pédagogiques / recrutement restent dérivées des tables métier,
    qui constituent la source de vérité. Cette table sert uniquement à l'usage produit : pages,
    recherches, clics et navigation.
    """

    class EventName(models.TextChoices):
        PAGE_VIEW = "page_view", "Page vue"
        SEARCH_SUBMITTED = "search_submitted", "Recherche lancée"
        DISCOVERY_RESULT_CLICKED = "discovery_result_clicked", "Résultat de recherche ouvert"
        RECOMMENDATION_CLICKED = "recommendation_clicked", "Recommandation ouverte"
        COURSE_VIEWED = "course_viewed", "Cours consulté"
        FORMATION_VIEWED = "formation_viewed", "Formation consultée"
        PDF_VIEWED = "pdf_viewed", "PDF consulté"
        OPPORTUNITY_VIEWED = "opportunity_viewed", "Opportunité consultée"
        VIDEO_STARTED = "video_started", "Vidéo démarrée"
        VIDEO_COMPLETED = "video_completed", "Vidéo terminée"

    event_name = models.CharField(max_length=64, choices=EventName.choices, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="product_events",
    )
    session_key = models.CharField(max_length=64, blank=True, db_index=True)
    path = models.CharField(max_length=240, blank=True, db_index=True)
    properties = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-occurred_at", "-id"]
        indexes = [
            models.Index(fields=["event_name", "-occurred_at"], name="analytics_event_time_idx"),
            models.Index(fields=["user", "-occurred_at"], name="analytics_user_time_idx"),
            models.Index(fields=["session_key", "-occurred_at"], name="analytics_session_time_idx"),
        ]

    def __str__(self):
        return f"{self.event_name} · {self.occurred_at:%Y-%m-%d %H:%M}"
