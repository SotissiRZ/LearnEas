from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("notifications", "0001_initial"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.AddField(model_name="notificationpreference", name="email_enabled", field=models.BooleanField(default=True)),
        migrations.AddField(model_name="notificationpreference", name="email_payment_enabled", field=models.BooleanField(default=True)),
        migrations.AddField(model_name="notificationpreference", name="email_live_enabled", field=models.BooleanField(default=True)),
        migrations.AddField(model_name="notificationpreference", name="email_inactivity_enabled", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="notificationpreference", name="email_certificate_enabled", field=models.BooleanField(default=True)),
        migrations.CreateModel(
            name="EmailDelivery",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("recipient", models.EmailField(db_index=True, max_length=254)),
                ("event_type", models.CharField(choices=[("welcome", "Bienvenue"), ("payment", "Paiement confirmé"), ("live", "Rappel de live"), ("inactivity", "Relance d'inactivité"), ("certificate", "Certificat disponible"), ("password_reset", "Réinitialisation du mot de passe"), ("session_invite", "Invitation à une séance"), ("test", "Test administrateur")], db_index=True, max_length=30)),
                ("event_key", models.CharField(max_length=220, unique=True)),
                ("subject", models.CharField(max_length=255)),
                ("template_key", models.CharField(default="transactional", max_length=80)),
                ("template_context", models.JSONField(blank=True, default=dict)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("provider_message_id", models.CharField(blank=True, db_index=True, max_length=180)),
                ("status", models.CharField(choices=[("queued", "En attente"), ("simulated", "Simulé"), ("sent", "Envoyé"), ("failed", "Échec"), ("skipped", "Ignoré")], db_index=True, default="queued", max_length=20)),
                ("provider_response", models.JSONField(blank=True, default=dict)),
                ("error", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("failed_at", models.DateTimeField(blank=True, null=True)),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="email_deliveries", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(model_name="emaildelivery", index=models.Index(fields=["status", "created_at"], name="notif_email_status_created_idx")),
        migrations.AddIndex(model_name="emaildelivery", index=models.Index(fields=["event_type", "created_at"], name="notif_email_event_created_idx")),
    ]
