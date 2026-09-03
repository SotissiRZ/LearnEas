from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Administrateur"
        INSTRUCTOR = "instructor", "Instructeur"
        STUDENT = "student", "Étudiant"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    bio = models.TextField(blank=True)
    country = models.CharField(max_length=100, blank=True)
    headline = models.CharField(max_length=255, blank=True, help_text="Ex: Expert Laravel & Django")
    years_experience = models.PositiveIntegerField(default=0)
    domain = models.CharField(max_length=150, blank=True, help_text="Domaine d'expertise (instructeur)")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"

    @property
    def is_instructor(self):
        return self.role == self.Role.INSTRUCTOR

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT


class PlatformSettings(models.Model):
    """Paramètres administrables de la plateforme.

    Une seule ligne (pk=1) est utilisée. Les valeurs d'environnement restent des
    valeurs de repli pour les installations existantes.
    """
    site_name = models.CharField(max_length=120, default="LearnEas")
    support_email = models.EmailField(default="support@learneas.com")
    registration_enabled = models.BooleanField(default=True)
    instructor_applications_enabled = models.BooleanField(default=True)
    platform_commission_percent = models.PositiveSmallIntegerField(default=15)
    minimum_payout_amount = models.DecimalField(max_digits=10, decimal_places=2, default=10)

    # Identité juridique / conformité
    legal_company_name = models.CharField(max_length=180, blank=True, default="LearnEas")
    legal_address = models.TextField(blank=True)
    legal_country = models.CharField(max_length=100, blank=True, default="Maroc")
    legal_registration_number = models.CharField(max_length=120, blank=True)
    legal_tax_number = models.CharField(max_length=120, blank=True)
    privacy_email = models.EmailField(blank=True, default="privacy@learneas.com")
    terms_updated_at = models.DateField(null=True, blank=True)
    privacy_updated_at = models.DateField(null=True, blank=True)
    refund_policy_days = models.PositiveSmallIntegerField(default=14)

    # Paramètres globaux des certificats. Les contenus peuvent les surcharger.
    certificate_verification_enabled = models.BooleanField(default=True)
    certificate_default_enabled = models.BooleanField(default=True)
    certificate_default_auto_issue = models.BooleanField(default=True)
    certificate_default_threshold_percent = models.PositiveSmallIntegerField(default=100)
    certificate_default_attendance_percent = models.PositiveSmallIntegerField(default=80)
    certificate_default_validity_months = models.PositiveIntegerField(null=True, blank=True)
    certificate_default_title = models.CharField(max_length=180, default="Certificat de réussite")
    certificate_default_subtitle = models.CharField(max_length=220, blank=True)
    certificate_default_signatory_name = models.CharField(max_length=180, blank=True)
    certificate_default_signatory_title = models.CharField(max_length=180, blank=True)
    certificate_default_accent_color = models.CharField(max_length=20, default="#1f6f5c")
    certificate_default_number_prefix = models.CharField(max_length=30, default="LE-CERT")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Paramètres de la plateforme"
        verbose_name_plural = "Paramètres de la plateforme"

    def save(self, *args, **kwargs):
        self.pk = 1
        self.platform_commission_percent = min(max(int(self.platform_commission_percent), 0), 100)
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        from django.conf import settings
        defaults = {
            "platform_commission_percent": getattr(settings, "PLATFORM_COMMISSION_PERCENT", 15),
            "minimum_payout_amount": getattr(settings, "MINIMUM_PAYOUT_AMOUNT", 10),
        }
        obj, _ = cls.objects.get_or_create(pk=1, defaults=defaults)
        return obj

    def __str__(self):
        return self.site_name

class InstructorApplication(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        APPROVED = "approved", "Approuvée"
        REJECTED = "rejected", "Refusée"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="instructor_application")
    domain = models.CharField(max_length=150)
    years_experience = models.PositiveIntegerField(default=0)
    headline = models.CharField(max_length=255, blank=True)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    review_note = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_instructor_applications"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} · {self.get_status_display()}"

