from django.contrib import admin
from .models import InteractiveFormation, FormationSession, FormationEnrollment


class FormationSessionInline(admin.TabularInline):
    model = FormationSession
    extra = 1


@admin.register(InteractiveFormation)
class InteractiveFormationAdmin(admin.ModelAdmin):
    list_display = ("title", "instructor", "status", "price", "num_sessions",
                     "students_count", "max_students", "published", "start_date")
    list_filter = ("status", "published", "level", "category")
    search_fields = ("title", "description")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [FormationSessionInline]


@admin.register(FormationSession)
class FormationSessionAdmin(admin.ModelAdmin):
    list_display = ("formation", "session_number", "scheduled_at", "completed")


@admin.register(FormationEnrollment)
class FormationEnrollmentAdmin(admin.ModelAdmin):
    list_display = ("user", "formation", "enrolled_at", "certificate_issued")
