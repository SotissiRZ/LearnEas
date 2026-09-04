from django.contrib import admin
from .models import AISettings, AIConversation, AIMessage, AIKnowledgeChunk, AIUsage, AIEvaluationCase


@admin.register(AISettings)
class AISettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Activation", {"fields": ("enabled", "rag_enabled", "history_enabled")}),
        ("Profils", {"fields": ("student_enabled", "instructor_enabled", "admin_enabled")}),
        ("Quotas mensuels", {"fields": ("student_monthly_limit", "instructor_monthly_limit", "admin_monthly_limit")}),
        ("Modèle", {"fields": ("default_model", "temperature", "max_output_tokens", "max_history_messages", "max_context_chunks", "input_cost_per_million_eur", "output_cost_per_million_eur")}),
        ("Instructions", {"fields": ("custom_system_prompt",)}),
    )
    def has_add_permission(self, request):
        return not AISettings.objects.exists()
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AIConversation)
class AIConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "archived", "updated_at")
    list_filter = ("archived", "updated_at")
    search_fields = ("user__email", "title")
    readonly_fields = ("created_at", "updated_at", "context_preview")


@admin.register(AIMessage)
class AIMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "role", "model", "created_at")
    list_filter = ("role", "provider", "model")
    search_fields = ("content", "conversation__user__email")
    readonly_fields = ("created_at", "feedback_at")


@admin.register(AIKnowledgeChunk)
class AIKnowledgeChunkAdmin(admin.ModelAdmin):
    list_display = ("id", "source_type", "title", "course", "pdf_product", "is_public", "updated_at")
    list_filter = ("source_type", "is_public")
    search_fields = ("title", "content")
    readonly_fields = ("updated_at",)


@admin.register(AIUsage)
class AIUsageAdmin(admin.ModelAdmin):
    list_display = ("user", "provider", "model", "prompt_tokens", "completion_tokens", "estimated_cost_eur", "rag_chunks", "latency_ms", "created_at")
    list_filter = ("provider", "model", "created_at")
    search_fields = ("user__email",)
    readonly_fields = ("request_id", "created_at")


@admin.register(AIEvaluationCase)
class AIEvaluationCaseAdmin(admin.ModelAdmin):
    list_display = ("id", "question", "expected_source_type", "expected_source_id", "enabled", "last_passed", "last_rank", "last_run_at")
    list_filter = ("enabled", "expected_source_type", "last_passed")
    search_fields = ("question", "notes")
    readonly_fields = ("last_passed", "last_rank", "last_run_at", "created_at")
