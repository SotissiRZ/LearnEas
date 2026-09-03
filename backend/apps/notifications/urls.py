from django.urls import path
from .views import (
    NotificationPreferenceView,
    AdminWhatsAppStatusView,
    AdminWhatsAppTestView,
    WhatsAppWebhookView,
)

urlpatterns = [
    path("preferences/", NotificationPreferenceView.as_view(), name="notification-preferences"),
    path("admin/whatsapp/status/", AdminWhatsAppStatusView.as_view(), name="admin-whatsapp-status"),
    path("admin/whatsapp/test/", AdminWhatsAppTestView.as_view(), name="admin-whatsapp-test"),
    path("whatsapp/webhook/", WhatsAppWebhookView.as_view(), name="whatsapp-webhook"),
]
