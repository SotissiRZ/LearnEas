from django.contrib import admin
from .models import (
    Currency, PaymentGateway, Order, OrderItem, PayoutProfile, InstructorPayout,
    PaymentAttempt, PaymentEvent, PaymentIssue,
)


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "symbol", "exchange_rate", "decimal_places", "is_active", "is_default", "sort_order")
    list_filter = ("is_active", "is_default", "decimal_places")
    search_fields = ("code", "name")
    ordering = ("sort_order", "code")


@admin.register(PaymentGateway)
class PaymentGatewayAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active", "sandbox", "sort_order")
    list_filter = ("is_active", "sandbox")
    search_fields = ("name", "code")
    ordering = ("sort_order", "name")



class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = (
        "item_type", "course", "pdf_product", "formation", "instructor", "unit_price",
        "platform_fee_amount", "instructor_earning_amount",
    )

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "user", "status", "provider", "currency", "total_amount", "created_at")
    list_filter = ("status", "provider", "provider_sandbox", "currency")
    search_fields = ("invoice_number", "user__email", "provider_reference")
    readonly_fields = (
        "user", "status", "provider", "provider_sandbox", "base_total_amount", "total_amount",
        "currency", "provider_reference", "provider_status", "payment_method", "last_provider_check_at", "expires_at",
        "invoice_number", "created_at", "paid_at",
    )
    inlines = [OrderItemInline]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PayoutProfile)
class PayoutProfileAdmin(admin.ModelAdmin):
    list_display = ("instructor", "method", "account_name", "updated_at")
    readonly_fields = ("instructor", "method", "account_name", "account_reference", "updated_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(InstructorPayout)
class InstructorPayoutAdmin(admin.ModelAdmin):
    list_display = ("instructor", "amount", "method", "status", "requested_at", "processed_at", "reference")
    list_filter = ("status", "method")
    search_fields = ("instructor__email", "instructor__username", "reference")
    readonly_fields = (
        "instructor", "amount", "status", "method", "account_reference_snapshot", "requested_at",
        "processed_at", "reference", "note",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(PaymentAttempt)
class PaymentAttemptAdmin(admin.ModelAdmin):
    list_display = ("order", "attempt_number", "provider", "provider_sandbox", "status", "provider_status", "check_count", "error_count", "started_at")
    list_filter = ("provider", "provider_sandbox", "status")
    search_fields = ("order__invoice_number", "provider_reference")
    readonly_fields = tuple(field.name for field in PaymentAttempt._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PaymentEvent)
class PaymentEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "provider", "provider_sandbox", "source", "event_type", "outcome", "order", "request_id")
    list_filter = ("provider", "provider_sandbox", "source", "outcome", "event_type")
    search_fields = ("order__invoice_number", "external_id", "request_id", "payload_hash")
    readonly_fields = tuple(field.name for field in PaymentEvent._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PaymentIssue)
class PaymentIssueAdmin(admin.ModelAdmin):
    list_display = ("created_at", "order", "issue_type", "severity", "status", "resolved_at")
    list_filter = ("status", "severity", "issue_type")
    search_fields = ("order__invoice_number", "order__user__email", "message")
    readonly_fields = tuple(field.name for field in PaymentIssue._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
