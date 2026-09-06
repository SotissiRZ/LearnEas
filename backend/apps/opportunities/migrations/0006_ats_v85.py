from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("opportunities", "0005_alter_opportunity_apply_mode"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="employerprofile",
            name="legal_name",
            field=models.CharField(blank=True, max_length=220),
        ),
        migrations.AddField(
            model_name="employerprofile",
            name="registration_number",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="employerprofile",
            name="registration_country",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="employerprofile",
            name="verification_document",
            field=models.FileField(blank=True, null=True, upload_to="employers/verification/%Y/%m/"),
        ),
        migrations.AddField(
            model_name="employerprofile",
            name="verification_status",
            field=models.CharField(
                choices=[
                    ("unverified", "Non vérifiée"),
                    ("pending", "Vérification en cours"),
                    ("verified", "Vérifiée"),
                    ("rejected", "Vérification refusée"),
                ],
                db_index=True,
                default="unverified",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="employerprofile",
            name="verification_note",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="employerprofile",
            name="verification_submitted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="employerprofile",
            name="identity_verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="employerprofile",
            name="identity_verified_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="identity_verified_employer_profiles",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.CreateModel(
            name="SavedTalentSearch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("search_text", models.CharField(blank=True, max_length=180)),
                ("country", models.CharField(blank=True, max_length=100)),
                (
                    "availability",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("immediate", "Disponible immédiatement"),
                            ("2_weeks", "Sous 2 semaines"),
                            ("1_month", "Sous 1 mois"),
                            ("open", "À l'écoute"),
                            ("unavailable", "Indisponible"),
                        ],
                        max_length=20,
                    ),
                ),
                ("min_experience", models.PositiveSmallIntegerField(default=0)),
                ("min_match_score", models.PositiveSmallIntegerField(default=0)),
                ("alerts_enabled", models.BooleanField(db_index=True, default=True)),
                ("last_checked_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("last_checked_candidate_id", models.PositiveBigIntegerField(default=0)),
                ("last_match_count", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "employer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="saved_talent_searches",
                        to="opportunities.employerprofile",
                    ),
                ),
                (
                    "opportunity",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="saved_talent_searches",
                        to="opportunities.opportunity",
                    ),
                ),
            ],
            options={"ordering": ["-updated_at", "-id"]},
        ),
        migrations.AddConstraint(
            model_name="savedtalentsearch",
            constraint=models.UniqueConstraint(
                fields=("employer", "name"), name="uniq_employer_saved_talent_search_name"
            ),
        ),
        migrations.AddConstraint(
            model_name="savedtalentsearch",
            constraint=models.CheckConstraint(
                condition=models.Q(("min_match_score__lte", 100)), name="saved_talent_match_lte_100"
            ),
        ),
        migrations.AddIndex(
            model_name="savedtalentsearch",
            index=models.Index(
                fields=["employer", "alerts_enabled", "-updated_at"], name="opp_saved_search_alert_idx"
            ),
        ),
    ]
