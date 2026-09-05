from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [("notifications", "0002_email_resend")]

    operations = [
        migrations.AddField(model_name="notificationpreference", name="in_app_enabled", field=models.BooleanField(default=True)),
        migrations.AddField(model_name="notificationpreference", name="whatsapp_recruitment_enabled", field=models.BooleanField(default=True)),
        migrations.AddField(model_name="notificationpreference", name="email_recruitment_enabled", field=models.BooleanField(default=True)),
        migrations.AlterField(model_name="whatsappdelivery", name="event_type", field=models.CharField(choices=[("payment", "Paiement confirmé"), ("live", "Rappel de live"), ("inactivity", "Relance d'inactivité"), ("certificate", "Certificat disponible"), ("recruitment", "Recrutement"), ("test", "Test administrateur")], db_index=True, max_length=20)),
        migrations.AlterField(model_name="emaildelivery", name="event_type", field=models.CharField(choices=[("welcome", "Bienvenue"), ("payment", "Paiement confirmé"), ("live", "Rappel de live"), ("inactivity", "Relance d'inactivité"), ("certificate", "Certificat disponible"), ("recruitment", "Recrutement"), ("password_reset", "Réinitialisation du mot de passe"), ("session_invite", "Invitation à une séance"), ("test", "Test administrateur")], db_index=True, max_length=30)),
        migrations.CreateModel(
            name="InAppNotification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_key", models.CharField(max_length=240, unique=True)),
                ("category", models.CharField(choices=[("system", "Système"), ("learning", "Apprentissage"), ("payment", "Paiement"), ("live", "Live"), ("mentorship", "Mentorat"), ("recruitment", "Recrutement"), ("certificate", "Certificat")], db_index=True, default="system", max_length=24)),
                ("event_type", models.CharField(db_index=True, max_length=64)),
                ("title", models.CharField(max_length=180)),
                ("body", models.TextField(blank=True)),
                ("action_url", models.CharField(blank=True, max_length=500)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("priority", models.CharField(choices=[("low", "Faible"), ("normal", "Normale"), ("high", "Haute")], db_index=True, default="normal", max_length=12)),
                ("read_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="in_app_notifications", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.AddIndex(model_name="inappnotification", index=models.Index(fields=["user", "read_at", "-created_at"], name="notif_inapp_user_read_idx")),
        migrations.AddIndex(model_name="inappnotification", index=models.Index(fields=["user", "category", "-created_at"], name="notif_inapp_user_cat_idx")),
    ]
