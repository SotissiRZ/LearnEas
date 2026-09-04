from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class EmployerProfile(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        APPROVED = "approved", "Approuvé"
        REJECTED = "rejected", "Refusé"
        SUSPENDED = "suspended", "Suspendu"

    class CompanySize(models.TextChoices):
        SOLO = "solo", "Indépendant"
        MICRO = "1-10", "1–10"
        SMALL = "11-50", "11–50"
        MEDIUM = "51-200", "51–200"
        LARGE = "201-1000", "201–1000"
        ENTERPRISE = "1000+", "1000+"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="employer_profile")
    company_name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True)
    industry = models.CharField(max_length=140, blank=True)
    company_size = models.CharField(max_length=20, choices=CompanySize.choices, blank=True)
    website_url = models.URLField(blank=True)
    logo = models.ImageField(upload_to="employers/logos/%Y/%m/", blank=True, null=True)
    country = models.CharField(max_length=100)
    city = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    review_note = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reviewed_employer_profiles",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["company_name"]
        indexes = [models.Index(fields=["status", "created_at"], name="opp_emp_status_created_idx")]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.company_name)[:180] or "entreprise"
            candidate = base
            n = 1
            while EmployerProfile.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                n += 1
                candidate = f"{base}-{n}"
            self.slug = candidate
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.company_name} · {self.get_status_display()}"


class CandidateProfile(models.Model):
    class Availability(models.TextChoices):
        IMMEDIATE = "immediate", "Disponible immédiatement"
        TWO_WEEKS = "2_weeks", "Sous 2 semaines"
        ONE_MONTH = "1_month", "Sous 1 mois"
        OPEN = "open", "À l'écoute"
        UNAVAILABLE = "unavailable", "Indisponible"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="candidate_profile")
    headline = models.CharField(max_length=180, blank=True)
    summary = models.TextField(blank=True)
    skills = models.JSONField(default=list, blank=True)
    desired_roles = models.JSONField(default=list, blank=True)
    preferred_kinds = models.JSONField(default=list, blank=True)
    preferred_work_modes = models.JSONField(default=list, blank=True)
    preferred_countries = models.JSONField(default=list, blank=True)
    minimum_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_currency = models.CharField(max_length=3, default="EUR")
    availability = models.CharField(max_length=20, choices=Availability.choices, default=Availability.OPEN)
    years_experience = models.PositiveSmallIntegerField(default=0)
    resume = models.FileField(upload_to="opportunities/resumes/%Y/%m/", blank=True, null=True)
    is_searchable = models.BooleanField(default=False, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [models.Index(fields=["is_searchable", "-updated_at"], name="opp_candidate_search_idx")]

    def __str__(self):
        return f"Candidat · {self.user}"


class Opportunity(models.Model):
    class Kind(models.TextChoices):
        JOB = "job", "Emploi"
        INTERNSHIP = "internship", "Stage"
        FREELANCE = "freelance", "Freelance"
        MISSION = "mission", "Mission"

    class ContractType(models.TextChoices):
        FULL_TIME = "full_time", "Temps plein"
        PART_TIME = "part_time", "Temps partiel"
        FIXED_TERM = "fixed_term", "CDD"
        PERMANENT = "permanent", "CDI"
        INTERNSHIP = "internship", "Stage"
        FREELANCE = "freelance", "Freelance"
        PROJECT = "project", "Projet / mission"

    class WorkMode(models.TextChoices):
        REMOTE = "remote", "À distance"
        HYBRID = "hybrid", "Hybride"
        ONSITE = "onsite", "Sur site"

    class ExperienceLevel(models.TextChoices):
        ENTRY = "entry", "Débutant / premier emploi"
        JUNIOR = "junior", "Junior"
        MID = "mid", "Intermédiaire"
        SENIOR = "senior", "Senior"
        LEAD = "lead", "Lead / management"

    class SalaryPeriod(models.TextChoices):
        HOUR = "hour", "Par heure"
        DAY = "day", "Par jour"
        MONTH = "month", "Par mois"
        YEAR = "year", "Par an"
        PROJECT = "project", "Forfait mission"

    class ApplyMode(models.TextChoices):
        INTERNAL = "internal", "Candidature KalanPro"
        EXTERNAL = "external", "Lien externe"

    class Status(models.TextChoices):
        DRAFT = "draft", "Brouillon"
        PUBLISHED = "published", "Publiée"
        CLOSED = "closed", "Clôturée"
        ARCHIVED = "archived", "Archivée"

    employer = models.ForeignKey(EmployerProfile, on_delete=models.PROTECT, related_name="opportunities")
    title = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240, unique=True, blank=True)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.JOB, db_index=True)
    contract_type = models.CharField(max_length=20, choices=ContractType.choices, default=ContractType.FULL_TIME)
    work_mode = models.CharField(max_length=20, choices=WorkMode.choices, default=WorkMode.REMOTE, db_index=True)
    experience_level = models.CharField(max_length=20, choices=ExperienceLevel.choices, default=ExperienceLevel.ENTRY)
    description = models.TextField()
    responsibilities = models.JSONField(default=list, blank=True)
    requirements = models.JSONField(default=list, blank=True)
    skills_required = models.JSONField(default=list, blank=True)
    skills_optional = models.JSONField(default=list, blank=True)
    country = models.CharField(max_length=100, blank=True, db_index=True)
    city = models.CharField(max_length=120, blank=True)
    remote_worldwide = models.BooleanField(default=False)
    salary_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_currency = models.CharField(max_length=3, default="EUR")
    salary_period = models.CharField(max_length=20, choices=SalaryPeriod.choices, default=SalaryPeriod.MONTH)
    show_salary = models.BooleanField(default=True)
    apply_mode = models.CharField(max_length=20, choices=ApplyMode.choices, default=ApplyMode.INTERNAL)
    external_application_url = models.URLField(blank=True)
    application_deadline = models.DateTimeField(null=True, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    featured = models.BooleanField(default=False, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-featured", "-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["status", "kind", "work_mode", "-published_at"], name="opp_listing_public_idx"),
            models.Index(fields=["employer", "status", "-created_at"], name="opp_listing_employer_idx"),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(f"{self.title}-{self.employer.company_name}")[:220] or "opportunite"
            candidate = base
            n = 1
            while Opportunity.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                n += 1
                candidate = f"{base}-{n}"
            self.slug = candidate
        if self.status == self.Status.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def is_open(self):
        if self.status != self.Status.PUBLISHED:
            return False
        return not self.application_deadline or self.application_deadline > timezone.now()

    def __str__(self):
        return f"{self.title} · {self.employer.company_name}"


class OpportunityApplication(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Candidature envoyée"
        REVIEWING = "reviewing", "En cours d'étude"
        SHORTLISTED = "shortlisted", "Présélectionné"
        INTERVIEW = "interview", "Entretien"
        OFFER = "offer", "Offre"
        HIRED = "hired", "Retenu"
        REJECTED = "rejected", "Non retenu"
        WITHDRAWN = "withdrawn", "Retirée"

    opportunity = models.ForeignKey(Opportunity, on_delete=models.PROTECT, related_name="applications")
    candidate = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="opportunity_applications")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED, db_index=True)
    cover_letter = models.TextField(blank=True)
    resume_file = models.FileField(upload_to="opportunities/applications/%Y/%m/", blank=True, null=True)
    share_portfolio = models.BooleanField(default=True)
    match_score = models.PositiveSmallIntegerField(default=0)

    # Snapshot professionnel au moment de la candidature.
    candidate_name_snapshot = models.CharField(max_length=220)
    candidate_email_snapshot = models.EmailField()
    country_snapshot = models.CharField(max_length=100, blank=True)
    headline_snapshot = models.CharField(max_length=180, blank=True)
    skills_snapshot = models.JSONField(default=list, blank=True)
    portfolio_snapshot = models.JSONField(default=dict, blank=True)
    certificates_snapshot = models.JSONField(default=list, blank=True)
    verified_projects_snapshot = models.JSONField(default=list, blank=True)

    recruiter_note = models.TextField(blank=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-applied_at"]
        constraints = [
            models.UniqueConstraint(fields=["opportunity", "candidate"], name="uniq_opportunity_candidate_application"),
        ]
        indexes = [
            models.Index(fields=["opportunity", "status", "-applied_at"], name="opp_app_listing_status_idx"),
            models.Index(fields=["candidate", "status", "-applied_at"], name="opp_app_candidate_status_idx"),
        ]

    def __str__(self):
        return f"{self.candidate} → {self.opportunity}"
