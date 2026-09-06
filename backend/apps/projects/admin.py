from django.contrib import admin
from .models import ProjectAssignment, ProjectSubmission, ProjectSubmissionRevision, PortfolioProfile, PortfolioItem, PortfolioCertificate


@admin.register(ProjectAssignment)
class ProjectAssignmentAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "published", "required_for_certificate", "passing_score", "order")
    list_filter = ("published", "required_for_certificate")
    search_fields = ("title", "course__title", "course__instructor__email")


@admin.register(ProjectSubmission)
class ProjectSubmissionAdmin(admin.ModelAdmin):
    list_display = ("assignment", "student", "status", "score", "submitted_at", "reviewed_at")
    list_filter = ("status",)
    search_fields = ("student__email", "assignment__title", "assignment__course__title")

admin.site.register(ProjectSubmissionRevision)
admin.site.register(PortfolioProfile)
admin.site.register(PortfolioItem)


@admin.register(PortfolioCertificate)
class PortfolioCertificateAdmin(admin.ModelAdmin):
    list_display = ("profile", "certificate", "is_public", "featured", "order", "updated_at")
    list_filter = ("is_public", "featured")
    search_fields = ("profile__slug", "profile__user__email", "certificate__certificate_number", "certificate__content_title")
