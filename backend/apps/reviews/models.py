from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class Review(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    course = models.ForeignKey("catalog.Course", on_delete=models.CASCADE, null=True, blank=True, related_name="reviews")
    pdf_product = models.ForeignKey("catalog.PDFProduct", on_delete=models.CASCADE, null=True, blank=True, related_name="reviews")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "course"], name="unique_review_per_course",
                                     condition=models.Q(course__isnull=False)),
            models.UniqueConstraint(fields=["user", "pdf_product"], name="unique_review_per_pdf",
                                     condition=models.Q(pdf_product__isnull=False)),
        ]

    def __str__(self):
        return f"{self.user} — {self.rating}★"


class LessonComment(models.Model):
    """Commentaire/question sous une vidéo, avec réponses (fil de discussion)."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lesson_comments")
    lesson = models.ForeignKey("catalog.Lesson", on_delete=models.CASCADE, related_name="comments")
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.user} sur {self.lesson}"
