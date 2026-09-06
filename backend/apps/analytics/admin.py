from django.contrib import admin
from .models import ProductEvent


@admin.register(ProductEvent)
class ProductEventAdmin(admin.ModelAdmin):
    list_display = ("event_name", "user", "path", "occurred_at")
    list_filter = ("event_name", "occurred_at")
    search_fields = ("path", "user__email", "session_key")
    readonly_fields = ("event_name", "user", "session_key", "path", "properties", "occurred_at")
    date_hierarchy = "occurred_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
