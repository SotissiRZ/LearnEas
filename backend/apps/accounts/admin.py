from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, PlatformSettings, InstructorApplication


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ("username", "email", "role", "is_active", "date_joined")
    list_filter = ("role", "is_active")
    fieldsets = UserAdmin.fieldsets + (
        ("KalanPro", {"fields": ("role", "avatar", "bio", "country", "headline", "domain", "years_experience")}),
    )


@admin.register(PlatformSettings)
class PlatformSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Identité", {"fields": ("site_name", "support_email")}),
        ("Accès", {"fields": ("registration_enabled", "instructor_applications_enabled")}),
        ("Finance", {"fields": ("platform_commission_percent", "minimum_payout_amount")}),
        ("Tarifs & modèle économique", {"fields": (
            "pricing_enabled",
            "instructor_pro_monthly_eur", "instructor_pro_commission_percent",
            "mentor_commission_percent",
            "employer_free_active_jobs", "employer_single_post_eur",
            "employer_pro_monthly_eur", "employer_pro_active_jobs",
            "employer_business_monthly_eur", "employer_business_active_jobs",
        )}),
        ("WhatsApp", {"fields": (
            "whatsapp_enabled", "whatsapp_template_language",
            "whatsapp_payment_template_name", "whatsapp_live_template_name",
            "whatsapp_inactivity_template_name", "whatsapp_certificate_template_name",
            "whatsapp_recruitment_template_name", "whatsapp_test_template_name", "whatsapp_live_reminder_minutes", "whatsapp_inactivity_days",
        )}),
        ("Email Resend", {"fields": (
            "resend_enabled", "resend_from_name", "resend_from_email", "resend_reply_to",
        )}),
    )

    def has_add_permission(self, request):
        return not PlatformSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

admin.site.register(InstructorApplication)
