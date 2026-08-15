from django.conf import settings
from django.db import models


class FAQ(models.Model):
    class Audience(models.TextChoices):
        ALL = "all", "Tout le monde"
        STUDENT = "student", "Étudiants"
        INSTRUCTOR = "instructor", "Instructeurs"

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="faqs")
    question = models.CharField(max_length=255)
    answer = models.TextField(blank=True)
    audience = models.CharField(max_length=20, choices=Audience.choices, default=Audience.ALL)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "FAQ"
        verbose_name_plural = "FAQ"

    def __str__(self):
        return self.question
