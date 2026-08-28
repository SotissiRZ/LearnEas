import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class FormationStatus(models.TextChoices):
    DRAFT = "draft", "Brouillon"
    SCHEDULED = "scheduled", "Planifiée"
    IN_PROGRESS = "in_progress", "En cours"
    COMPLETED = "completed", "Terminée"
    CANCELLED = "cancelled", "Annulée"


class InteractiveFormation(models.Model):
    """Formation interactive en direct, hébergée dans une salle LearnEas."""

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
    """Séance planifiée dans une salle vidéo interne LearnEas."""

    formation = models.ForeignKey(InteractiveFormation, on_delete=models.CASCADE, related_name="sessions")
    session_number = models.PositiveIntegerField()
    scheduled_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    # Conservé uniquement pour compatibilité avec les anciennes données/migrations. L'API ne
    # demande plus et n'expose plus de lien de réunion externe.
    meeting_link = models.URLField(blank=True, help_text="Champ historique — non utilisé par LearnEas")
    room_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    actual_duration_seconds = models.PositiveIntegerField(default=0)
    completed = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["session_number"]
        unique_together = ("formation", "session_number")

    def __str__(self):
        return f"{self.formation.title} — Séance {self.session_number}"

    @property
    def actual_duration_minutes(self):
        seconds = self.actual_duration_seconds
        if not seconds and self.started_at:
            end = self.ended_at or timezone.now()
            seconds = max(int((end - self.started_at).total_seconds()), 0)
        return round(seconds / 60, 1)


class FormationEnrollment(models.Model):
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


class FormationAttendance(models.Model):
    class Role(models.TextChoices):
        ORGANIZER = "organizer", "Organisateur"
        PARTICIPANT = "participant", "Participant"
        ADMIN = "admin", "Administrateur"

    session = models.ForeignKey(FormationSession, on_delete=models.CASCADE, related_name="attendance_records")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="formation_attendances")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.PARTICIPANT)
    joined_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["joined_at"]
        indexes = [models.Index(fields=["session", "user", "left_at"])]

    def close(self, when=None):
        when = when or timezone.now()
        self.last_seen_at = when
        self.left_at = when
        self.duration_seconds = max(int((when - self.joined_at).total_seconds()), 0)
        self.save(update_fields=["last_seen_at", "left_at", "duration_seconds"])


class FormationSignal(models.Model):
    """Messages éphémères de signalisation WebRTC (offer/answer/ICE) entre participants."""

    class Kind(models.TextChoices):
        OFFER = "offer", "Offer"
        ANSWER = "answer", "Answer"
        ICE = "ice", "ICE candidate"

    session = models.ForeignKey(FormationSession, on_delete=models.CASCADE, related_name="signals")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_formation_signals")
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_formation_signals")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        indexes = [models.Index(fields=["session", "recipient", "id"])]
