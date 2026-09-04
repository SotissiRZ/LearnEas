from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AIConversationViewSet, status_view, chat_view, admin_settings_view, admin_metrics_view

router = DefaultRouter()
router.register("conversations", AIConversationViewSet, basename="ai-conversation")

urlpatterns = [
    path("", include(router.urls)),
    path("status/", status_view, name="ai-status"),
    path("chat/", chat_view, name="ai-chat"),
    path("admin/settings/", admin_settings_view, name="ai-admin-settings"),
    path("admin/metrics/", admin_metrics_view, name="ai-admin-metrics"),
]
