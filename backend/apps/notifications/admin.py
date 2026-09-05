from django.contrib import admin
from .models import NotificationPreference, WhatsAppDelivery, EmailDelivery, InAppNotification


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "whatsapp_phone", "whatsapp_opt_in", "email_enabled", "updated_at")
    list_filter = ("whatsapp_opt_in", "whatsapp_payment_enabled", "whatsapp_live_enabled", "whatsapp_inactivity_enabled", "whatsapp_certificate_enabled")
    search_fields = ("user__email", "user__first_name", "user__last_name", "whatsapp_phone")


@admin.register(WhatsAppDelivery)
class WhatsAppDeliveryAdmin(admin.ModelAdmin):
    list_display = ("event_type", "recipient", "status", "template_name", "created_at")
    list_filter = ("event_type", "status", "language_code")
    search_fields = ("recipient", "event_key", "provider_message_id", "user__email")
    readonly_fields = ("created_at", "sent_at", "delivered_at", "read_at", "failed_at")


@admin.register(EmailDelivery)
class EmailDeliveryAdmin(admin.ModelAdmin):
    list_display = ("event_type", "recipient", "status", "subject", "created_at")
    list_filter = ("event_type", "status")
    search_fields = ("recipient", "event_key", "provider_message_id", "user__email", "subject")
    readonly_fields = ("created_at", "sent_at", "failed_at")


@admin.register(InAppNotification)
class InAppNotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "category", "title", "priority", "read_at", "created_at")
    list_filter = ("category", "priority", "read_at", "created_at")
    search_fields = ("title", "body", "user__email", "event_key")
    readonly_fields = ("event_key", "created_at", "read_at")
