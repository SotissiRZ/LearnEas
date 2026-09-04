from django.apps import AppConfig


class AssistantAIConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.assistant_ai"
    verbose_name = "Assistant IA KalanPro"

    def ready(self):
        from . import signals  # noqa: F401
