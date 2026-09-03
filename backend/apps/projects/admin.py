from django.contrib import admin
from .models import ProjectAssignment, ProjectSubmission, ProjectSubmissionRevision, PortfolioProfile, PortfolioItem


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
