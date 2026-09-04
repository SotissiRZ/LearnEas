from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AIConversationViewSet, status_view, chat_view, admin_settings_view, admin_metrics_view, message_feedback_view, admin_evaluate_rag_view

router = DefaultRouter()
router.register("conversations", AIConversationViewSet, basename="ai-conversation")

urlpatterns = [
    path("", include(router.urls)),
    path("status/", status_view, name="ai-status"),
    path("chat/", chat_view, name="ai-chat"),
    path("messages/<int:message_id>/feedback/", message_feedback_view, name="ai-message-feedback"),
    path("admin/settings/", admin_settings_view, name="ai-admin-settings"),
    path("admin/metrics/", admin_metrics_view, name="ai-admin-metrics"),
    path("admin/evaluate-rag/", admin_evaluate_rag_view, name="ai-admin-evaluate-rag"),
]
