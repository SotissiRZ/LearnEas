from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AIConversationViewSet, status_view, chat_view, admin_settings_view, admin_metrics_view, message_feedback_view, admin_evaluate_rag_view, action_confirm_view, action_reject_view, drafts_view, admin_actions_view, attachment_upload_view, attachment_delete_view, attachment_download_view, draft_export_view

router = DefaultRouter()
router.register("conversations", AIConversationViewSet, basename="ai-conversation")

urlpatterns = [
    path("", include(router.urls)),
    path("status/", status_view, name="ai-status"),
    path("chat/", chat_view, name="ai-chat"),
    path("attachments/", attachment_upload_view, name="ai-attachment-upload"),
    path("attachments/<int:attachment_id>/", attachment_delete_view, name="ai-attachment-delete"),
    path("attachments/<int:attachment_id>/download/", attachment_download_view, name="ai-attachment-download"),
    path("messages/<int:message_id>/feedback/", message_feedback_view, name="ai-message-feedback"),
    path("actions/<uuid:token>/confirm/", action_confirm_view, name="ai-action-confirm"),
    path("actions/<uuid:token>/reject/", action_reject_view, name="ai-action-reject"),
    path("drafts/", drafts_view, name="ai-drafts"),
    path("drafts/<int:draft_id>/export/", draft_export_view, name="ai-draft-export"),
    path("admin/settings/", admin_settings_view, name="ai-admin-settings"),
    path("admin/metrics/", admin_metrics_view, name="ai-admin-metrics"),
    path("admin/actions/", admin_actions_view, name="ai-admin-actions"),
    path("admin/evaluate-rag/", admin_evaluate_rag_view, name="ai-admin-evaluate-rag"),
]
