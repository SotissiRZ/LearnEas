from django.contrib import admin
from .models import EmployerProfile, CandidateProfile, Opportunity, OpportunityApplication


@admin.register(EmployerProfile)
class EmployerProfileAdmin(admin.ModelAdmin):
    list_display = ("company_name", "country", "industry", "status", "created_at")
    list_filter = ("status", "country", "company_size")
    search_fields = ("company_name", "user__email", "industry", "city")
    readonly_fields = ("slug", "reviewed_at", "created_at", "updated_at")


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
