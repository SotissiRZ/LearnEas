from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_platformsettings"),
    ]

    operations = [
        migrations.CreateModel(
            name="InstructorApplication",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("domain", models.CharField(max_length=150)),
                ("years_experience", models.PositiveIntegerField(default=0)),
                ("headline", models.CharField(blank=True, max_length=255)),
                ("message", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("pending", "En attente"), ("approved", "Approuvée"), ("rejected", "Refusée")], db_index=True, default="pending", max_length=20)),
                ("review_note", models.TextField(blank=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviewed_instructor_applications", to=settings.AUTH_USER_MODEL)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="instructor_application", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
