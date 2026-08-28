from django.contrib import admin
from .models import Order, OrderItem, PayoutProfile, InstructorPayout


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("instructor", "platform_fee_amount", "instructor_earning_amount")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "user", "status", "provider", "total_amount", "created_at")
    list_filter = ("status", "provider")
    inlines = [OrderItemInline]


@admin.register(PayoutProfile)
class PayoutProfileAdmin(admin.ModelAdmin):
    list_display = ("instructor", "method", "account_name", "updated_at")


@admin.register(InstructorPayout)
class InstructorPayoutAdmin(admin.ModelAdmin):
    list_display = ("instructor", "amount", "method", "status", "requested_at", "processed_at", "reference")
    list_filter = ("status", "method")
    search_fields = ("instructor__email", "instructor__username", "reference")
