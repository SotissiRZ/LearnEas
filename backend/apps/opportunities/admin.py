from django.contrib import admin
from django.utils.html import format_html
from apps.common.fields import sign_private_media_name
from .models import (
    EmployerProfile, CandidateProfile, Opportunity, OpportunityApplication, TalentBookmark,
    TalentAccessLog, EmployerEntitlement, ApplicationHistoryEvent, RecruitmentInterview, EmploymentOffer, SavedTalentSearch,
)


@admin.register(EmployerProfile)
class EmployerProfileAdmin(admin.ModelAdmin):
    list_display = ("company_name", "country", "industry", "company_size", "status", "verification_status", "created_at")
    list_filter = ("status", "verification_status", "country", "company_size")
    search_fields = ("company_name", "user__email", "industry", "city")
    readonly_fields = (
        "slug", "reviewed_at", "verification_submitted_at", "identity_verified_at",
        "verification_document_secure", "created_at", "updated_at",
    )
    fieldsets = (("Identité", {"fields": ("user", "company_name", "slug", "tagline", "description", "industry", "company_size", "founded_year")}), ("Branding", {"fields": ("logo", "banner", "brand_color")}), ("Contact", {"fields": ("website_url", "linkedin_url", "contact_email", "country", "city")}), ("Marque employeur", {"fields": ("values", "benefits", "hiring_regions")}), ("Vérification entreprise", {"fields": ("legal_name", "registration_number", "registration_country", "verification_document_secure", "verification_status", "verification_note", "verification_submitted_at", "identity_verified_by", "identity_verified_at")}), ("Validation du profil", {"fields": ("status", "review_note", "reviewed_by", "reviewed_at", "created_at", "updated_at")}))

    @admin.display(description="Justificatif")
    def verification_document_secure(self, obj):
        if not obj or not obj.verification_document:
            return "Aucun justificatif"
        url = sign_private_media_name(obj.verification_document.name)
        if not url:
            return "Justificatif indisponible"
        return format_html('<a href="{}" target="_blank" rel="noopener noreferrer">Ouvrir le justificatif</a>', url)


@admin.register(CandidateProfile)
class CandidateProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "headline", "availability", "years_experience", "is_searchable", "updated_at")
    list_filter = ("availability", "is_searchable")
    search_fields = ("user__email", "user__first_name", "user__last_name", "headline")


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = ("title", "employer", "kind", "work_mode", "country", "status", "application_deadline", "published_at")
    list_filter = ("status", "kind", "work_mode", "experience_level", "country", "featured")
    search_fields = ("title", "employer__company_name", "description", "skills_required")
    prepopulated_fields = {}
    readonly_fields = ("slug", "published_at", "created_at", "updated_at")


@admin.register(OpportunityApplication)
class OpportunityApplicationAdmin(admin.ModelAdmin):
    list_display = ("candidate_name_snapshot", "opportunity", "status", "match_score", "applied_at")
    list_filter = ("status", "opportunity__kind")
    search_fields = ("candidate_name_snapshot", "candidate_email_snapshot", "opportunity__title", "skills_snapshot")
    readonly_fields = (
        "match_score", "candidate_name_snapshot", "candidate_email_snapshot", "country_snapshot", "headline_snapshot",
        "skills_snapshot", "portfolio_snapshot", "certificates_snapshot", "verified_projects_snapshot", "applied_at", "updated_at",
    )


@admin.register(TalentBookmark)
class TalentBookmarkAdmin(admin.ModelAdmin):
    list_display = ("employer", "talent", "updated_at")
    search_fields = ("employer__company_name", "talent__user__email", "talent__headline")
    readonly_fields = ("created_at", "updated_at")


@admin.register(EmployerEntitlement)
class EmployerEntitlementAdmin(admin.ModelAdmin):
    list_display = ("employer", "kind", "order", "starts_at", "ends_at", "consumed_at", "revoked_at")
    list_filter = ("kind", "revoked_at")
    search_fields = ("employer__company_name", "employer__user__email", "entitlement_key", "order__invoice_number")
    readonly_fields = ("created_at", "updated_at", "consumed_at", "revoked_at")


@admin.register(TalentAccessLog)
class TalentAccessLogAdmin(admin.ModelAdmin):
    list_display = ("candidate", "employer", "access_type", "created_at")
    list_filter = ("access_type", "created_at")
    search_fields = ("candidate__user__email", "employer__company_name")
    readonly_fields = ("candidate", "employer", "recruiter", "access_type", "created_at")


@admin.register(ApplicationHistoryEvent)
class ApplicationHistoryEventAdmin(admin.ModelAdmin):
    list_display = ("application", "event_type", "actor", "created_at")
    list_filter = ("event_type", "created_at")
    readonly_fields = ("application", "actor", "event_type", "label", "metadata", "created_at")


@admin.register(RecruitmentInterview)
class RecruitmentInterviewAdmin(admin.ModelAdmin):
    list_display = ("application", "scheduled_at", "mode", "status")
    list_filter = ("mode", "status")
    search_fields = ("application__candidate_email_snapshot", "application__opportunity__title")


@admin.register(EmploymentOffer)
class EmploymentOfferAdmin(admin.ModelAdmin):
    list_display = ("application", "status", "salary_amount", "salary_currency", "expires_at", "responded_at")
    list_filter = ("status", "salary_currency")
    search_fields = ("application__candidate_email_snapshot", "application__opportunity__title", "title")

@admin.register(SavedTalentSearch)
class SavedTalentSearchAdmin(admin.ModelAdmin):
    list_display = ("name", "employer", "opportunity", "min_match_score", "alerts_enabled", "last_checked_at", "last_match_count")
    list_filter = ("alerts_enabled", "availability", "country")
    search_fields = ("name", "employer__company_name", "search_text", "opportunity__title")
    readonly_fields = ("last_checked_at", "last_match_count", "created_at", "updated_at")

