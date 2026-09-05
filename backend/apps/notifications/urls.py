from django.urls import path
from .views import (
    NotificationPreferenceView,
    AdminWhatsAppStatusView,
    AdminWhatsAppTestView,
    WhatsAppWebhookView,
    NotificationCenterView, NotificationUnreadCountView, NotificationReadView, NotificationReadAllView,
)

urlpatterns = [
    path("", NotificationCenterView.as_view(), name="notification-center"),
    path("unread-count/", NotificationUnreadCountView.as_view(), name="notification-unread-count"),
    path("<int:pk>/read/", NotificationReadView.as_view(), name="notification-read"),
    path("read-all/", NotificationReadAllView.as_view(), name="notification-read-all"),
    path("preferences/", NotificationPreferenceView.as_view(), name="notification-preferences"),
    path("admin/whatsapp/status/", AdminWhatsAppStatusView.as_view(), name="admin-whatsapp-status"),
    path("admin/whatsapp/test/", AdminWhatsAppTestView.as_view(), name="admin-whatsapp-test"),
    path("whatsapp/webhook/", WhatsAppWebhookView.as_view(), name="whatsapp-webhook"),
]
