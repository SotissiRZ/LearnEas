import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def populate_room_keys(apps, schema_editor):
    """Assign a different room UUID to every pre-existing session.

    The field must be added as nullable/non-unique first. Adding a UNIQUE field
    with ``default=uuid.uuid4`` directly to a table that already contains rows
    makes PostgreSQL use one migration-time default value for all existing rows,
    which violates the unique constraint.
    """

    FormationSession = apps.get_model("formations", "FormationSession")
    for session in FormationSession.objects.filter(room_key__isnull=True).iterator():
        session.room_key = uuid.uuid4()
        session.save(update_fields=["room_key"])


class Migration(migrations.Migration):
    dependencies = [
        ("formations", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # IMPORTANT: do not add this field as UNIQUE + default in one operation
        # when FormationSession already contains rows. See populate_room_keys().
        migrations.AddField(
            model_name="formationsession",
            name="room_key",
            field=models.UUIDField(blank=True, editable=False, null=True),
        ),
        migrations.RunPython(populate_room_keys, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="formationsession",
            name="room_key",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AddField(
            model_name="formationsession",
            name="started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="formationsession",
            name="ended_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="formationsession",
            name="actual_duration_seconds",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name="formationsession",
            name="meeting_link",
            field=models.URLField(blank=True, help_text="Champ historique — non utilisé par LearnEas"),
        ),
        migrations.CreateModel(
            name="FormationAttendance",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("organizer", "Organisateur"), ("participant", "Participant"), ("admin", "Administrateur")], default="participant", max_length=20)),
                ("joined_at", models.DateTimeField(auto_now_add=True)),
                ("last_seen_at", models.DateTimeField(auto_now_add=True)),
                ("left_at", models.DateTimeField(blank=True, null=True)),
                ("duration_seconds", models.PositiveIntegerField(default=0)),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attendance_records", to="formations.formationsession")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="formation_attendances", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["joined_at"]},
        ),
        migrations.AddIndex(
            model_name="formationattendance",
            index=models.Index(fields=["session", "user", "left_at"], name="formations__session_727f67_idx"),
        ),
        migrations.CreateModel(
            name="FormationSignal",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("offer", "Offer"), ("answer", "Answer"), ("ice", "ICE candidate")], max_length=10)),
                ("payload", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("recipient", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="received_formation_signals", to=settings.AUTH_USER_MODEL)),
                ("sender", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sent_formation_signals", to=settings.AUTH_USER_MODEL)),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="signals", to="formations.formationsession")),
            ],
            options={"ordering": ["id"]},
        ),
        migrations.AddIndex(
            model_name="formationsignal",
            index=models.Index(fields=["session", "recipient", "id"], name="formations__session_7c3f3c_idx"),
        ),
    ]
