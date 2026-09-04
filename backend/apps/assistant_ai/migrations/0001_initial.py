# Generated manually for KalanPro AI phase 1.
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("catalog", "0006_domain_category_domain"),
    ]
    operations = [
        migrations.CreateModel(
            name="AISettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("enabled", models.BooleanField(default=True)),
                ("rag_enabled", models.BooleanField(default=True)),
                ("history_enabled", models.BooleanField(default=True)),
                ("student_enabled", models.BooleanField(default=True)),
                ("instructor_enabled", models.BooleanField(default=True)),
                ("admin_enabled", models.BooleanField(default=True)),
                ("default_model", models.CharField(blank=True, help_text="Vide = modèle défini par AI_CHAT_MODEL dans l'environnement.", max_length=120)),
                ("student_monthly_limit", models.PositiveIntegerField(default=20)),
                ("instructor_monthly_limit", models.PositiveIntegerField(default=100)),
                ("admin_monthly_limit", models.PositiveIntegerField(default=500)),
                ("max_history_messages", models.PositiveSmallIntegerField(default=12)),
                ("max_context_chunks", models.PositiveSmallIntegerField(default=6)),
                ("max_output_tokens", models.PositiveIntegerField(default=1200)),
                ("temperature", models.DecimalField(decimal_places=2, default=0.3, max_digits=3)),
                ("custom_system_prompt", models.TextField(blank=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "Configuration Assistant IA", "verbose_name_plural": "Configuration Assistant IA"},
        ),
        migrations.CreateModel(
            name="AIConversation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(default="Nouvelle conversation", max_length=120)),
                ("context_preview", models.JSONField(blank=True, default=dict)),
                ("archived", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ai_conversations", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-updated_at"]},
        ),
        migrations.CreateModel(
            name="AIKnowledgeChunk",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_type", models.CharField(choices=[("course", "Cours"), ("lesson", "Leçon / transcript"), ("pdf_resource", "PDF de cours"), ("pdf_product", "PDF autonome")], max_length=30)),
                ("source_id", models.PositiveIntegerField()),
                ("chunk_index", models.PositiveSmallIntegerField(default=0)),
                ("title", models.CharField(max_length=240)),
                ("content", models.TextField()),
                ("source_path", models.CharField(blank=True, max_length=500)),
                ("is_public", models.BooleanField(default=False)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("course", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="ai_chunks", to="catalog.course")),
                ("instructor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ai_knowledge_chunks", to=settings.AUTH_USER_MODEL)),
                ("pdf_product", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="ai_chunks", to="catalog.pdfproduct")),
            ],
            options={"ordering": ["source_type", "source_id", "chunk_index"]},
        ),
        migrations.CreateModel(
            name="AIMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("user", "Utilisateur"), ("assistant", "Assistant")], max_length=20)),
                ("content", models.TextField()),
                ("sources", models.JSONField(blank=True, default=list)),
                ("provider", models.CharField(blank=True, max_length=80)),
                ("model", models.CharField(blank=True, max_length=120)),
                ("prompt_tokens", models.PositiveIntegerField(default=0)),
                ("completion_tokens", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("conversation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="assistant_ai.aiconversation")),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.CreateModel(
            name="AIUsage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("request_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("provider", models.CharField(blank=True, max_length=80)),
                ("model", models.CharField(blank=True, max_length=120)),
                ("prompt_tokens", models.PositiveIntegerField(default=0)),
                ("completion_tokens", models.PositiveIntegerField(default=0)),
                ("latency_ms", models.PositiveIntegerField(default=0)),
                ("rag_chunks", models.PositiveSmallIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("conversation", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="usage_entries", to="assistant_ai.aiconversation")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ai_usage", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(model_name="aiknowledgechunk", constraint=models.UniqueConstraint(fields=("source_type", "source_id", "chunk_index"), name="uniq_ai_source_chunk")),
        migrations.AddIndex(model_name="aiconversation", index=models.Index(fields=["user", "archived", "updated_at"], name="ai_conv_user_arch_idx")),
        migrations.AddIndex(model_name="aimessage", index=models.Index(fields=["conversation", "created_at"], name="ai_msg_conv_created_idx")),
        migrations.AddIndex(model_name="aiknowledgechunk", index=models.Index(fields=["source_type", "source_id"], name="ai_chunk_source_idx")),
        migrations.AddIndex(model_name="aiknowledgechunk", index=models.Index(fields=["course", "is_public"], name="ai_chunk_course_pub_idx")),
        migrations.AddIndex(model_name="aiknowledgechunk", index=models.Index(fields=["pdf_product", "is_public"], name="ai_chunk_pdf_pub_idx")),
        migrations.AddIndex(model_name="aiusage", index=models.Index(fields=["user", "created_at"], name="ai_usage_user_date_idx")),
    ]
