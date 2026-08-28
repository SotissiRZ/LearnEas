from django.contrib import admin
from .models import InteractiveFormation, FormationSession, FormationEnrollment, FormationAttendance, FormationSignal


class FormationSessionInline(admin.TabularInline):
    model = FormationSession
    extra = 0
    fields = ("session_number", "scheduled_at", "duration_minutes", "started_at", "ended_at", "completed")
    readonly_fields = ("started_at", "ended_at")


@admin.register(InteractiveFormation)
class InteractiveFormationAdmin(admin.ModelAdmin):
    list_display = ("title", "instructor", "status", "price", "num_sessions", "students_count", "max_students", "published", "start_date")
    list_filter = ("status", "published", "level", "category")
    search_fields = ("title", "description")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [FormationSessionInline]


@admin.register(FormationSession)
class FormationSessionAdmin(admin.ModelAdmin):
    list_display = ("formation", "session_number", "scheduled_at", "started_at", "ended_at", "actual_duration_minutes", "completed")
    list_filter = ("completed", "formation")


@admin.register(FormationEnrollment)
class FormationEnrollmentAdmin(admin.ModelAdmin):
    list_display = ("user", "formation", "enrolled_at", "certificate_issued")


@admin.register(FormationAttendance)
class FormationAttendanceAdmin(admin.ModelAdmin):
    list_display = ("session", "user", "role", "joined_at", "left_at", "duration_seconds")
    list_filter = ("role", "session__formation")
    search_fields = ("user__email", "user__username", "session__formation__title")


@admin.register(FormationSignal)
class FormationSignalAdmin(admin.ModelAdmin):
    list_display = ("session", "sender", "recipient", "kind", "created_at")
    readonly_fields = ("session", "sender", "recipient", "kind", "payload", "created_at")
