import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_legal_certificate_settings"),
        ("catalog", "0003_course_certificates_lesson_accessibility"),
        ("formations", "0003_formation_certificates"),
        ("enrollments", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Certificate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("certificate_number", models.CharField(db_index=True, max_length=80, unique=True)),
                ("verification_code", models.UUIDField(db_index=True, default=uuid.uuid4, unique=True)),
                ("status", models.CharField(choices=[("active", "Valide"), ("revoked", "Révoqué"), ("expired", "Expiré")], db_index=True, default="active", max_length=20)),
                ("issued_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("revocation_reason", models.TextField(blank=True)),
                ("achievement_percent", models.DecimalField(decimal_places=2, default=100, max_digits=5)),
                ("student_name", models.CharField(max_length=220)),
                ("content_type", models.CharField(choices=[("course", "Cours"), ("formation", "Formation")], max_length=20)),
                ("content_title", models.CharField(max_length=240)),
                ("instructor_name", models.CharField(blank=True, max_length=220)),
                ("title", models.CharField(default="Certificat de réussite", max_length=180)),
                ("subtitle", models.CharField(blank=True, max_length=220)),
                ("description", models.TextField(blank=True)),
                ("signatory_name", models.CharField(blank=True, max_length=180)),
                ("signatory_title", models.CharField(blank=True, max_length=180)),
                ("accent_color", models.CharField(default="#1f6f5c", max_length=20)),
                ("duration_minutes", models.PositiveIntegerField(default=0)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("display_options", models.JSONField(blank=True, default=dict)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("course_enrollment", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="certificate_record", to="enrollments.courseenrollment")),
                ("formation_enrollment", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="certificate_record", to="formations.formationenrollment")),
                ("issued_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="issued_certificates", to="accounts.user")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="certificates", to="accounts.user")),
            ],
            options={"ordering": ["-issued_at"]},
        ),
        migrations.AddConstraint(
            model_name="certificate",
            constraint=models.CheckConstraint(
                check=(models.Q(course_enrollment__isnull=False, formation_enrollment__isnull=True) | models.Q(course_enrollment__isnull=True, formation_enrollment__isnull=False)),
                name="certificate_exactly_one_enrollment",
            ),
        ),
    ]
