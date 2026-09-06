import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class ActiveEntitlementManager(models.Manager):
    """Manager par défaut : seuls les droits encore actifs sont visibles par les contrôles d'accès."""
    def get_queryset(self):
        now = timezone.now()
        return super().get_queryset().filter(revoked_at__isnull=True).filter(models.Q(access_expires_at__isnull=True) | models.Q(access_expires_at__gt=now))


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
    source_order = models.ForeignKey(
        "payments.Order", on_delete=models.SET_NULL, null=True, blank=True, related_name="course_entitlements"
    )
    source_subscription = models.ForeignKey(
        "payments.LearnerSubscription", on_delete=models.SET_NULL, null=True, blank=True, related_name="course_entitlements"
    )
    access_expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    revoked_at = models.DateTimeField(null=True, blank=True, db_index=True)
    revocation_reason = models.CharField(max_length=255, blank=True)

    objects = ActiveEntitlementManager()
    all_objects = models.Manager()

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
    last_position_seconds = models.PositiveIntegerField(default=0)
    last_watch_heartbeat_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("enrollment", "lesson")


class PDFPurchase(models.Model):
    """Achat d'un PDF vendu SEUL."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pdf_purchases")
    pdf_product = models.ForeignKey("catalog.PDFProduct", on_delete=models.CASCADE, related_name="purchases")
    purchased_at = models.DateTimeField(auto_now_add=True)
    source_order = models.ForeignKey(
        "payments.Order", on_delete=models.SET_NULL, null=True, blank=True, related_name="pdf_entitlements"
    )
    source_subscription = models.ForeignKey(
        "payments.LearnerSubscription", on_delete=models.SET_NULL, null=True, blank=True, related_name="pdf_entitlements"
    )
    access_expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    revoked_at = models.DateTimeField(null=True, blank=True, db_index=True)
    revocation_reason = models.CharField(max_length=255, blank=True)

    objects = ActiveEntitlementManager()
    all_objects = models.Manager()

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
        constraints = [
            models.CheckConstraint(
                check=(models.Q(course__isnull=False, pdf_product__isnull=True) | models.Q(course__isnull=True, pdf_product__isnull=False)),
                name="wishlist_exactly_one_target",
            ),
            models.UniqueConstraint(fields=["user", "course"], condition=models.Q(course__isnull=False), name="uniq_wishlist_course"),
            models.UniqueConstraint(fields=["user", "pdf_product"], condition=models.Q(pdf_product__isnull=False), name="uniq_wishlist_pdf"),
        ]


class Certificate(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Valide"
        REVOKED = "revoked", "Révoqué"
        EXPIRED = "expired", "Expiré"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="certificates")
    # Plusieurs versions peuvent exister pour une même inscription (révocation / expiration / réémission).
    # Les anciens certificats restent vérifiables au lieu d'être écrasés.
    course_enrollment = models.ForeignKey(
        CourseEnrollment, on_delete=models.SET_NULL, null=True, blank=True, related_name="certificate_records"
    )
    formation_enrollment = models.ForeignKey(
        "formations.FormationEnrollment", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="certificate_records",
    )
    supersedes = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="replacement_certificates"
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

    # Preuves publiques figées au moment de l'émission. Elles ne dépendent plus des
    # modifications ultérieures du cours, du portfolio ou des paramètres de la plateforme.
    issuer_name = models.CharField(max_length=180, blank=True)
    issuer_country = models.CharField(max_length=100, blank=True)
    skills_snapshot = models.JSONField(default=list, blank=True)
    projects_snapshot = models.JSONField(default=list, blank=True)
    credential_digest = models.CharField(max_length=64, blank=True, db_index=True)
    schema_version = models.PositiveSmallIntegerField(default=2)

    class Meta:
        ordering = ["-issued_at"]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(course_enrollment__isnull=False, formation_enrollment__isnull=False),
                name="certificate_not_two_enrollments",
            ),
            models.UniqueConstraint(
                fields=["course_enrollment"],
                condition=models.Q(course_enrollment__isnull=False, status="active"),
                name="uniq_active_course_certificate",
            ),
            models.UniqueConstraint(
                fields=["formation_enrollment"],
                condition=models.Q(formation_enrollment__isnull=False, status="active"),
                name="uniq_active_formation_certificate",
            ),
        ]

    def __str__(self):
        return f"{self.certificate_number} · {self.student_name}"

    @property
    def effective_status(self):
        from django.utils import timezone
        if self.status == self.Status.REVOKED:
            return self.Status.REVOKED
        if self.status == self.Status.EXPIRED:
            return self.Status.EXPIRED
        if self.expires_at and self.expires_at <= timezone.now():
            return self.Status.EXPIRED
        return self.Status.ACTIVE


class CertificateEvent(models.Model):
    class EventType(models.TextChoices):
        ISSUED = "issued", "Émis"
        REVOKED = "revoked", "Révoqué"
        REISSUED = "reissued", "Réémis"
        EXPIRED = "expired", "Expiré"

    certificate = models.ForeignKey(Certificate, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=20, choices=EventType.choices, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="certificate_events"
    )
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["certificate", "-created_at"], name="cert_event_cert_created_idx")]

    def __str__(self):
        return f"{self.certificate.certificate_number} · {self.event_type}"


class LessonNote(models.Model):
    """Note privée de l'apprenant, attachée à un instant précis d'une leçon."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lesson_notes")
    lesson = models.ForeignKey("catalog.Lesson", on_delete=models.CASCADE, related_name="learner_notes")
    timestamp_seconds = models.PositiveIntegerField(default=0)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["lesson__section__order", "lesson__order", "timestamp_seconds", "created_at"]
        indexes = [
            models.Index(fields=["user", "lesson", "timestamp_seconds"], name="enr_note_user_lesson_ts"),
        ]

    def __str__(self):
        return f"{self.user} · {self.lesson} @ {self.timestamp_seconds}s"
