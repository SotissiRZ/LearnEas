from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import apps.formations.models


class Migration(migrations.Migration):

    dependencies = [
        ("formations", "0004_formation_query_indexes"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="formationattendance",
            name="hand_raised",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="formationsignal",
            name="kind",
            field=models.CharField(
                choices=[
                    ("offer", "Offer"),
                    ("answer", "Answer"),
                    ("ice", "ICE candidate"),
                    ("chat", "Chat"),
                    ("control", "Moderation control"),
                ],
                max_length=10,
            ),
        ),
        migrations.CreateModel(
            name="FormationRoomFile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(upload_to=apps.formations.models.formation_room_file_upload_to)),
                ("original_name", models.CharField(max_length=255)),
                ("content_type", models.CharField(blank=True, max_length=120)),
                ("size", models.PositiveBigIntegerField(default=0)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                (
                    "session",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="room_files", to="formations.formationsession"),
                ),
                (
                    "uploader",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="formation_room_files", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={"ordering": ["-uploaded_at"]},
        ),
        migrations.AddIndex(
            model_name="formationroomfile",
            index=models.Index(fields=["session", "-uploaded_at"], name="formations_session_94ff2c_idx"),
        ),
    ]
