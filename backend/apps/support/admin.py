from django.contrib import admin
from .models import SupportTicket, SupportMessage, ModerationReport, ModerationActionLog


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ("reference", "subject", "requester", "category", "priority", "status", "assigned_to", "updated_at")
    list_filter = ("status", "priority", "category")
    search_fields = ("reference", "subject", "requester__email")
    readonly_fields = ("reference", "created_at", "updated_at", "last_message_at")


@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    list_display = ("ticket", "author", "is_staff_reply", "created_at")
    search_fields = ("ticket__reference", "author__email", "body")


@admin.register(ModerationReport)
class ModerationReportAdmin(admin.ModelAdmin):
    list_display = ("id", "target_type", "target_label", "reason", "severity", "status", "reporter", "assigned_to", "created_at")
    list_filter = ("status", "severity", "reason", "target_type")
    search_fields = ("target_label", "target_id", "details", "reporter__email")


admin.site.register(ModerationActionLog)
