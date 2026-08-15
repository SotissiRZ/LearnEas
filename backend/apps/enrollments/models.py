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
