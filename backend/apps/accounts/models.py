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
