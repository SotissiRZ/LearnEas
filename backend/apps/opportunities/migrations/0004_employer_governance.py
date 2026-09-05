from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("opportunities", "0003_recruiter_workspace"),
        ("payments", "0013_employer_entitlement_code"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TalentAccessLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("access_type", models.CharField(choices=[("profile", "Consultation du profil"), ("bookmark", "Ajout aux favoris"), ("application", "Consultation via candidature")], default="profile", max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("candidate", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="access_logs", to="opportunities.candidateprofile")),
                ("employer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="talent_access_logs", to="opportunities.employerprofile")),
                ("recruiter", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="talent_access_logs", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.CreateModel(
            name="EmployerEntitlement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("single_post", "Annonce à l'unité"), ("pro", "Pro recrutement"), ("business", "Business")], db_index=True, max_length=32)),
                ("entitlement_key", models.CharField(blank=True, help_text="Identifiant métier extensible du droit payé ; dimensionné pour les futurs identifiants prestataire.", max_length=191)),
                ("starts_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("ends_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("revocation_reason", models.CharField(blank=True, max_length=500)),
                ("consumed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("consumed_by", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="consumed_single_post_entitlement", to="opportunities.opportunity")),
                ("employer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="entitlements", to="opportunities.employerprofile")),
                ("order", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="employer_entitlement", to="payments.order")),
            ],
            options={"ordering": ["-starts_at", "-created_at"]},
        ),
        migrations.AddField(
            model_name="opportunity",
            name="publication_entitlement",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="published_opportunities", to="opportunities.employerentitlement"),
        ),
        migrations.CreateModel(
            name="ApplicationHistoryEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(db_index=True, max_length=64)),
                ("label", models.CharField(max_length=220)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="recruitment_history_events", to=settings.AUTH_USER_MODEL)),
                ("application", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="history_events", to="opportunities.opportunityapplication")),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.CreateModel(
            name="RecruitmentInterview",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("scheduled_at", models.DateTimeField(db_index=True)),
                ("duration_minutes", models.PositiveSmallIntegerField(default=45)),
                ("mode", models.CharField(choices=[("video", "Visioconférence"), ("phone", "Téléphone"), ("onsite", "Sur site")], default="video", max_length=20)),
                ("location_or_url", models.CharField(blank=True, max_length=500)),
                ("candidate_message", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("scheduled", "Planifié"), ("completed", "Terminé"), ("cancelled", "Annulé")], db_index=True, default="scheduled", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("application", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="interviews", to="opportunities.opportunityapplication")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_recruitment_interviews", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["scheduled_at", "id"]},
        ),
        migrations.CreateModel(
            name="EmploymentOffer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(default="Proposition d'embauche", max_length=220)),
                ("message", models.TextField(blank=True)),
                ("salary_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("salary_currency", models.CharField(default="EUR", max_length=3)),
                ("start_date", models.DateField(blank=True, null=True)),
                ("expires_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("status", models.CharField(choices=[("pending", "En attente"), ("accepted", "Acceptée"), ("declined", "Refusée"), ("withdrawn", "Retirée")], db_index=True, default="pending", max_length=20)),
                ("responded_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("application", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="employment_offer", to="opportunities.opportunityapplication")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_employment_offers", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(model_name="talentaccesslog", index=models.Index(fields=["candidate", "-created_at"], name="opp_taccess_candidate_idx")),
        migrations.AddIndex(model_name="talentaccesslog", index=models.Index(fields=["employer", "-created_at"], name="opp_taccess_employer_idx")),
        migrations.AddIndex(model_name="employerentitlement", index=models.Index(fields=["employer", "kind", "revoked_at", "starts_at"], name="opp_entitlement_lookup_idx")),
        migrations.AddIndex(model_name="applicationhistoryevent", index=models.Index(fields=["application", "-created_at"], name="opp_app_history_idx")),
        migrations.AddIndex(model_name="recruitmentinterview", index=models.Index(fields=["application", "status", "scheduled_at"], name="opp_interview_app_idx")),
    ]
