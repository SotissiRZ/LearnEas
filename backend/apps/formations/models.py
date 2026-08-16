from django.conf import settings
from django.db import models
from django.utils.text import slugify


class FormationStatus(models.TextChoices):
    DRAFT = "draft", "Brouillon"
    SCHEDULED = "scheduled", "Planifiée"
    IN_PROGRESS = "in_progress", "En cours"
    COMPLETED = "completed", "Terminée"
    CANCELLED = "cancelled", "Annulée"


class InteractiveFormation(models.Model):
    """
    Formation interactive en direct (visioconférence) avec un ou deux formateurs,
    dispensée en un nombre fixe de séances planifiées à des apprenants inscrits.
    Reprend la fonctionnalité "formation interactive" du cahier des charges d'origine.
    """
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="interactive_formations"
    )
    co_instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="co_interactive_formations",
    )
    category = models.ForeignKey(
        "catalog.Category", on_delete=models.SET_NULL, null=True, related_name="interactive_formations"
    )

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField()
    level = models.CharField(
        max_length=20,
        choices=[("beginner", "Débutant"), ("intermediate", "Intermédiaire"), ("expert", "Expert")],
        default="beginner",
    )
    language = models.CharField(max_length=50, default="Français")

    price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    num_sessions = models.PositiveIntegerField(default=1, help_text="Nombre de séances de la formation")
    session_duration_minutes = models.PositiveIntegerField(default=60)
    max_students = models.PositiveIntegerField(default=10, help_text="Places disponibles")

    thumbnail = models.ImageField(upload_to="formations/thumbnails/", blank=True, null=True)

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=FormationStatus.choices, default=FormationStatus.DRAFT)

    published = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)
            slug = base
            i = 1
            while InteractiveFormation.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                i += 1
                slug = f"{base}-{i}"
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @property
    def students_count(self):
        return self.enrollments.count()

    @property
    def seats_left(self):
        return max(self.max_students - self.students_count, 0)

    @property
    def is_full(self):
        return self.seats_left <= 0


class FormationSession(models.Model):
    """Une séance planifiée (visioconférence) au sein d'une formation interactive."""
    formation = models.ForeignKey(InteractiveFormation, on_delete=models.CASCADE, related_name="sessions")
    session_number = models.PositiveIntegerField()
    scheduled_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    meeting_link = models.URLField(blank=True, help_text="Lien de visioconférence (Jitsi, Zoom, Meet...)")
    completed = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["session_number"]
        unique_together = ("formation", "session_number")

    def __str__(self):
        return f"{self.formation.title} — Séance {self.session_number}"


class FormationEnrollment(models.Model):
    """Inscription (après achat) d'un apprenant à une formation interactive."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="formation_enrollments"
    )
    formation = models.ForeignKey(InteractiveFormation, on_delete=models.CASCADE, related_name="enrollments")
    enrolled_at = models.DateTimeField(auto_now_add=True)
    attended_sessions = models.ManyToManyField(FormationSession, blank=True, related_name="attendees")
    certificate_issued = models.BooleanField(default=False)

    class Meta:
        unique_together = ("user", "formation")
        ordering = ["-enrolled_at"]

    def __str__(self):
        return f"{self.user} → {self.formation}"
