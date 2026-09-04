from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.utils.text import slugify


class ProjectAssignment(models.Model):
    """Projet pratique rattaché à un cours KalanPro."""

    course = models.ForeignKey("catalog.Course", on_delete=models.CASCADE, related_name="project_assignments")
    title = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240, blank=True)
    brief = models.TextField()
    instructions = models.TextField(blank=True)
    objectives = models.JSONField(default=list, blank=True)
    deliverables = models.JSONField(default=list, blank=True)
    skills = models.JSONField(default=list, blank=True)
    due_days_after_enrollment = models.PositiveSmallIntegerField(null=True, blank=True)
    max_score = models.PositiveSmallIntegerField(default=100)
    passing_score = models.PositiveSmallIntegerField(default=60)
    required_for_certificate = models.BooleanField(default=False)
    allow_resubmission = models.BooleanField(default=True)
    max_resubmissions = models.PositiveSmallIntegerField(null=True, blank=True)
    published = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["course_id", "order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["course", "slug"], name="uniq_project_assignment_course_slug"),
        ]
        indexes = [
            models.Index(fields=["course", "published", "order"], name="proj_assign_course_pub_idx"),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:210] or "projet"
            candidate = base
            n = 1
            while ProjectAssignment.objects.filter(course_id=self.course_id, slug=candidate).exclude(pk=self.pk).exists():
                n += 1
                candidate = f"{base}-{n}"
            self.slug = candidate
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.course} · {self.title}"


class ProjectSubmission(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Brouillon"
        SUBMITTED = "submitted", "À corriger"
        CHANGES_REQUESTED = "changes_requested", "Modifications demandées"
        APPROVED = "approved", "Validé"
        REJECTED = "rejected", "Refusé"

    assignment = models.ForeignKey(ProjectAssignment, on_delete=models.PROTECT, related_name="submissions")
    enrollment = models.ForeignKey("enrollments.CourseEnrollment", on_delete=models.CASCADE, related_name="project_submissions")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_submissions")
    title = models.CharField(max_length=220, blank=True)
    summary = models.TextField(blank=True)
    external_url = models.URLField(blank=True)
    repository_url = models.URLField(blank=True)
    artifact_file = models.FileField(upload_to="projects/submissions/%Y/%m/", blank=True, null=True)
    cover_image = models.ImageField(upload_to="projects/covers/%Y/%m/", blank=True, null=True)
    skills = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT, db_index=True)
    score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    instructor_feedback = models.TextField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_project_submissions"
    )
    resubmission_count = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(fields=["assignment", "student"], name="uniq_project_submission_assignment_student"),
        ]
        indexes = [
            models.Index(fields=["assignment", "status", "-updated_at"], name="proj_sub_assign_status_idx"),
            models.Index(fields=["student", "status", "-updated_at"], name="proj_sub_student_status_idx"),
        ]

    @property
    def is_late(self):
        if not self.assignment.due_days_after_enrollment or not self.submitted_at:
            return False
        due = self.enrollment.purchased_at + timedelta(days=self.assignment.due_days_after_enrollment)
        return self.submitted_at > due

    def __str__(self):
        return f"{self.student} · {self.assignment}"


class ProjectSubmissionRevision(models.Model):
    """Snapshot immuable de chaque remise afin de conserver l'historique pédagogique."""

    submission = models.ForeignKey(ProjectSubmission, on_delete=models.CASCADE, related_name="revisions")
    revision_number = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=220, blank=True)
    summary = models.TextField(blank=True)
    external_url = models.URLField(blank=True)
    repository_url = models.URLField(blank=True)
    artifact_file = models.FileField(upload_to="projects/revisions/%Y/%m/", blank=True, null=True)
    cover_image = models.ImageField(upload_to="projects/revision-covers/%Y/%m/", blank=True, null=True)
    skills = models.JSONField(default=list, blank=True)
    submitted_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-revision_number"]
        constraints = [
            models.UniqueConstraint(fields=["submission", "revision_number"], name="uniq_project_submission_revision"),
        ]

    def __str__(self):
        return f"{self.submission_id} · v{self.revision_number}"


class PortfolioProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="portfolio_profile")
    slug = models.SlugField(max_length=100, unique=True)
    is_public = models.BooleanField(default=False, db_index=True)
    title = models.CharField(max_length=180, blank=True)
    about = models.TextField(blank=True)
    skills = models.JSONField(default=list, blank=True)
    website_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    open_to_work = models.BooleanField(default=False)
    show_country = models.BooleanField(default=True)
    show_project_scores = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["slug"]

    def __str__(self):
        return f"Portfolio · {self.user}"


class PortfolioItem(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="portfolio_items")
    source_submission = models.OneToOneField(
        ProjectSubmission, on_delete=models.SET_NULL, null=True, blank=True, related_name="portfolio_item"
    )
    title = models.CharField(max_length=220)
    description = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to="portfolio/items/%Y/%m/", blank=True, null=True)
    external_url = models.URLField(blank=True)
    repository_url = models.URLField(blank=True)
    skills = models.JSONField(default=list, blank=True)
    is_public = models.BooleanField(default=True, db_index=True)
    featured = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    # Snapshot de la validation KalanPro. Un élément vérifié reste vérifiable même si
    # l'instructeur archive ensuite le projet ou le cours.
    is_verified = models.BooleanField(default=False, editable=False)
    verified_course_title = models.CharField(max_length=220, blank=True, editable=False)
    verified_assignment_title = models.CharField(max_length=220, blank=True, editable=False)
    verified_instructor_name = models.CharField(max_length=220, blank=True, editable=False)
    verified_at = models.DateTimeField(null=True, blank=True, editable=False)
    verified_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, editable=False)
    verified_max_score = models.PositiveSmallIntegerField(null=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-featured", "order", "-updated_at"]
        indexes = [
            models.Index(fields=["owner", "is_public", "featured"], name="portfolio_owner_public_idx"),
        ]

    def __str__(self):
        return f"{self.owner} · {self.title}"
