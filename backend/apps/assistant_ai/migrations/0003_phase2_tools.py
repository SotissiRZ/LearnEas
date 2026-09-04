import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("assistant_ai", "0002_quality_feedback_costs"),
        ("catalog", "0006_domain_category_domain"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="aisettings",
            name="tools_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="aimessage",
            name="actions",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.CreateModel(
            name="AIDraft",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("quiz", "Quiz"), ("course_outline", "Plan de cours")], max_length=30)),
                ("title", models.CharField(max_length=220)),
                ("payload", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("course", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ai_drafts", to="catalog.course")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ai_drafts", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-updated_at"]},
        ),
        migrations.CreateModel(
            name="AIActionLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("confirmation_token", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("tool_name", models.CharField(max_length=80)),
                ("label", models.CharField(max_length=220)),
                ("request_payload", models.JSONField(default=dict)),
                ("result_payload", models.JSONField(blank=True, default=dict)),
                ("status", models.CharField(choices=[("proposed", "À confirmer"), ("executed", "Exécutée"), ("rejected", "Refusée"), ("failed", "Échec")], db_index=True, default="proposed", max_length=20)),
                ("error", models.CharField(blank=True, max_length=1000)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("executed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("conversation", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="actions", to="assistant_ai.aiconversation")),
                ("message", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="action_logs", to="assistant_ai.aimessage")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ai_actions", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(model_name="aidraft", index=models.Index(fields=["user", "kind", "-updated_at"], name="ai_draft_user_kind_idx")),
        migrations.AddIndex(model_name="aiactionlog", index=models.Index(fields=["user", "status", "-created_at"], name="ai_action_user_status_idx")),
        migrations.AddIndex(model_name="aiactionlog", index=models.Index(fields=["tool_name", "status", "-created_at"], name="ai_action_tool_status_idx")),
    ]
