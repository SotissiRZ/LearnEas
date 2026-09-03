from django.contrib import admin
from .models import InteractiveFormation, FormationSession, FormationEnrollment, FormationAttendance, FormationSignal, FormationRoomFile, FormationSessionInvite, MentorshipOffering, MentorshipSlot, MentorshipBooking


class FormationSessionInline(admin.TabularInline):
    model = FormationSession
    extra = 0
    fields = ("session_number", "scheduled_at", "duration_minutes", "started_at", "ended_at", "completed")
    readonly_fields = ("started_at", "ended_at")


@admin.register(InteractiveFormation)
class InteractiveFormationAdmin(admin.ModelAdmin):
    list_display = ("title", "instructor", "status", "price", "num_sessions", "students_count", "max_students", "published", "start_date")
    list_filter = ("kind", "status", "published", "level", "category")
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


@admin.register(FormationRoomFile)
class FormationRoomFileAdmin(admin.ModelAdmin):
    list_display = ("session", "original_name", "uploader", "size", "uploaded_at")
    list_filter = ("session__formation", "content_type")
    search_fields = ("original_name", "uploader__email", "uploader__username")
    readonly_fields = ("session", "uploader", "file", "original_name", "content_type", "size", "uploaded_at")


@admin.register(FormationSessionInvite)
class FormationSessionInviteAdmin(admin.ModelAdmin):
    list_display = ("session", "email", "invited_by", "invited_user", "created_at", "accepted_at", "revoked_at")
    list_filter = ("session__formation",)
    search_fields = ("email", "invited_user__email", "session__formation__title")
    readonly_fields = ("token", "created_at", "accepted_at", "revoked_at")


@admin.register(MentorshipOffering)
class MentorshipOfferingAdmin(admin.ModelAdmin):
    list_display = ("title", "instructor", "duration_minutes", "price", "published", "timezone")
    list_filter = ("published", "language")
    search_fields = ("title", "description", "instructor__email")
    readonly_fields = ("room_formation", "created_at", "updated_at")


@admin.register(MentorshipSlot)
class MentorshipSlotAdmin(admin.ModelAdmin):
    list_display = ("offering", "starts_at", "is_active", "session")
    list_filter = ("is_active", "offering__instructor")
    search_fields = ("offering__title", "offering__instructor__email")


@admin.register(MentorshipBooking)
class MentorshipBookingAdmin(admin.ModelAdmin):
    list_display = ("user", "offering", "slot", "status", "price_snapshot", "confirmed_at")
    list_filter = ("status", "offering__instructor")
    search_fields = ("user__email", "offering__title", "offering__instructor__email")
    readonly_fields = ("price_snapshot", "expires_at", "confirmed_at", "cancelled_at", "created_at", "updated_at")
