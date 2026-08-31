import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("formations", "0006_shared_code_signal"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="FormationSessionInvite",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.EmailField(max_length=254)),
                ("token", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("accepted_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("invited_by", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sent_formation_session_invites", to=settings.AUTH_USER_MODEL)),
                ("invited_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="formation_session_invites", to=settings.AUTH_USER_MODEL)),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="email_invites", to="formations.formationsession")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="formationsessioninvite",
            constraint=models.UniqueConstraint(fields=("session", "email"), name="uniq_session_invite_email"),
        ),
        migrations.AddIndex(
            model_name="formationsessioninvite",
            index=models.Index(fields=["session", "email"], name="form_inv_sess_email_idx"),
        ),
        migrations.AlterField(
            model_name="formationattendance",
            name="role",
            field=models.CharField(choices=[("organizer", "Organisateur"), ("participant", "Participant"), ("guest", "Invité"), ("admin", "Administrateur")], default="participant", max_length=20),
        ),
    ]
