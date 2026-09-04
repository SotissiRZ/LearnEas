from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import apps.assistant_ai.models


class Migration(migrations.Migration):
    dependencies = [
        ("assistant_ai", "0005_career_copilot_drafts"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="aisettings",
            name="attachments_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="aisettings",
            name="max_attachment_mb",
            field=models.PositiveSmallIntegerField(default=12),
        ),
        migrations.AddField(
            model_name="aisettings",
            name="max_attachments_per_message",
            field=models.PositiveSmallIntegerField(default=5),
        ),
        migrations.AddField(
            model_name="aisettings",
            name="max_attachment_text_chars",
            field=models.PositiveIntegerField(default=12000),
        ),
        migrations.CreateModel(
            name="AIAttachment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(upload_to=apps.assistant_ai.models.ai_attachment_upload_to)),
                ("original_name", models.CharField(max_length=220)),
                ("mime_type", models.CharField(blank=True, max_length=120)),
                ("extension", models.CharField(max_length=16)),
                ("size_bytes", models.PositiveIntegerField(default=0)),
                ("extracted_text", models.TextField(blank=True)),
                ("extraction_status", models.CharField(choices=[("ready", "Texte extrait"), ("image", "Image"), ("no_text", "Aucun texte extractible"), ("failed", "Extraction échouée")], default="no_text", max_length=20)),
                ("extraction_error", models.CharField(blank=True, max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("conversation", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="attachments", to="assistant_ai.aiconversation")),
                ("message", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="attachments", to="assistant_ai.aimessage")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ai_attachments", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.AddIndex(model_name="aiattachment", index=models.Index(fields=["user", "created_at"], name="ai_attach_user_date_idx")),
        migrations.AddIndex(model_name="aiattachment", index=models.Index(fields=["conversation", "created_at"], name="ai_attach_conv_date_idx")),
    ]
