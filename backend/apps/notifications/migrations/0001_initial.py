# Generated manually for LearnEas v44.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("accounts", "0006_whatsapp_platform_settings"),
    ]

    operations = [
        migrations.CreateModel(
            name="NotificationPreference",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("whatsapp_phone", models.CharField(blank=True, help_text="Numéro WhatsApp au format international E.164, ex. +221771234567.", max_length=32)),
                ("whatsapp_opt_in", models.BooleanField(default=False)),
                ("whatsapp_payment_enabled", models.BooleanField(default=True)),
                ("whatsapp_live_enabled", models.BooleanField(default=True)),
                ("whatsapp_inactivity_enabled", models.BooleanField(default=True)),
                ("whatsapp_certificate_enabled", models.BooleanField(default=True)),
                ("whatsapp_consent_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="notification_preferences", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="WhatsAppDelivery",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("recipient", models.CharField(max_length=32)),
                ("event_type", models.CharField(choices=[("payment", "Paiement confirmé"), ("live", "Rappel de live"), ("inactivity", "Relance d'inactivité"), ("certificate", "Certificat disponible"), ("test", "Test administrateur")], db_index=True, max_length=20)),
                ("event_key", models.CharField(max_length=180, unique=True)),
                ("template_name", models.CharField(max_length=120)),
                ("language_code", models.CharField(default="fr", max_length=16)),
                ("variables", models.JSONField(blank=True, default=list)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("provider_message_id", models.CharField(blank=True, db_index=True, max_length=180)),
                ("status", models.CharField(choices=[("queued", "En attente"), ("simulated", "Simulé"), ("sent", "Envoyé"), ("delivered", "Livré"), ("read", "Lu"), ("failed", "Échec"), ("skipped", "Ignoré")], db_index=True, default="queued", max_length=20)),
                ("provider_response", models.JSONField(blank=True, default=dict)),
                ("error", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("delivered_at", models.DateTimeField(blank=True, null=True)),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                ("failed_at", models.DateTimeField(blank=True, null=True)),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="whatsapp_deliveries", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="whatsappdelivery",
            index=models.Index(fields=["status", "created_at"], name="notif_wa_status_created_idx"),
        ),
        migrations.AddIndex(
            model_name="whatsappdelivery",
            index=models.Index(fields=["event_type", "created_at"], name="notif_wa_event_created_idx"),
        ),
    ]
