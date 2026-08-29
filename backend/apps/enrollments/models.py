import uuid
from django.conf import settings
from django.db import models


class CourseEnrollment(models.Model):
    """Accès acquis à un cours COMPLET (playlist), jamais à une seule vidéo."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey("catalog.Course", on_delete=models.CASCADE, related_name="enrollments")
    purchased_at = models.DateTimeField(auto_now_add=True)
    progress_percent = models.PositiveSmallIntegerField(default=0)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    certificate_issued = models.BooleanField(default=False)
    last_accessed_lesson = models.ForeignKey(
        "catalog.Lesson", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        unique_together = ("user", "course")
        ordering = ["-purchased_at"]

    def __str__(self):
        return f"{self.user} → {self.course}"


class LessonProgress(models.Model):
    enrollment = models.ForeignKey(CourseEnrollment, on_delete=models.CASCADE, related_name="lesson_progress")
    lesson = models.ForeignKey("catalog.Lesson", on_delete=models.CASCADE, related_name="progress_entries")
    completed = models.BooleanField(default=False)
    watched_seconds = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("enrollment", "lesson")


class PDFPurchase(models.Model):
    """Achat d'un PDF vendu SEUL."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pdf_purchases")
    pdf_product = models.ForeignKey("catalog.PDFProduct", on_delete=models.CASCADE, related_name="purchases")
    purchased_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "pdf_product")
        ordering = ["-purchased_at"]

    def __str__(self):
        return f"{self.user} → {self.pdf_product}"


class Wishlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlist")
    course = models.ForeignKey("catalog.Course", on_delete=models.CASCADE, null=True, blank=True)
    pdf_product = models.ForeignKey("catalog.PDFProduct", on_delete=models.CASCADE, null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-added_at"]


class Certificate(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Valide"
        REVOKED = "revoked", "Révoqué"
        EXPIRED = "expired", "Expiré"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="certificates")
    course_enrollment = models.OneToOneField(
        CourseEnrollment, on_delete=models.CASCADE, null=True, blank=True, related_name="certificate_record"
    )
    formation_enrollment = models.OneToOneField(
        "formations.FormationEnrollment", on_delete=models.CASCADE, null=True, blank=True,
        related_name="certificate_record",
    )
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="issued_certificates",
    )
    certificate_number = models.CharField(max_length=80, unique=True, db_index=True)
    verification_code = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revocation_reason = models.TextField(blank=True)
    achievement_percent = models.DecimalField(max_digits=5, decimal_places=2, default=100)

    # Snapshot : le certificat émis ne change pas si le contenu/profil est modifié plus tard.
    student_name = models.CharField(max_length=220)
    content_type = models.CharField(max_length=20, choices=[("course", "Cours"), ("formation", "Formation")])
    content_title = models.CharField(max_length=240)
    instructor_name = models.CharField(max_length=220, blank=True)
    title = models.CharField(max_length=180, default="Certificat de réussite")
    subtitle = models.CharField(max_length=220, blank=True)
    description = models.TextField(blank=True)
    signatory_name = models.CharField(max_length=180, blank=True)
    signatory_title = models.CharField(max_length=180, blank=True)
    accent_color = models.CharField(max_length=20, default="#1f6f5c")
    duration_minutes = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)
    display_options = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-issued_at"]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(course_enrollment__isnull=False, formation_enrollment__isnull=True)
                    | models.Q(course_enrollment__isnull=True, formation_enrollment__isnull=False)
                ),
                name="certificate_exactly_one_enrollment",
            )
        ]

    def __str__(self):
        return f"{self.certificate_number} — {self.student_name}"

    @property
    def effective_status(self):
        from django.utils import timezone
        if self.status == self.Status.REVOKED:
            return self.Status.REVOKED
        if self.expires_at and self.expires_at <= timezone.now():
            return self.Status.EXPIRED
        return self.Status.ACTIVE
