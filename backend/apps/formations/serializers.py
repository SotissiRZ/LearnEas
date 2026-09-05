from django.conf import settings
from rest_framework import serializers
from apps.accounts.serializers import UserPublicCompactSerializer
from apps.catalog.serializers import CategoryCompactSerializer
from apps.common.fields import RelativeImageField
from apps.common.media_metadata import validate_upload_limits
from .models import (
    InteractiveFormation, FormationSession, FormationEnrollment, FormationAttendance, FormationSessionInvite,
    MentorshipOffering, MentorshipSlot, MentorshipBooking,
)


def _is_manager(user, formation):
    return bool(
        user and user.is_authenticated and (
            user.role == "admin" or formation.instructor_id == user.id or formation.co_instructor_id == user.id
        )
    )


class FormationSessionSerializer(serializers.ModelSerializer):
    actual_duration_minutes = serializers.ReadOnlyField()
    can_join = serializers.SerializerMethodField()
    formation_id = serializers.IntegerField(source="formation.id", read_only=True)
    formation_title = serializers.CharField(source="formation.title", read_only=True)
    organizer_name = serializers.SerializerMethodField()

    class Meta:
        model = FormationSession
        fields = [
            "id", "formation_id", "formation_title", "organizer_name", "session_number",
            "scheduled_at", "duration_minutes", "completed", "notes", "started_at",
            "ended_at", "actual_duration_seconds", "actual_duration_minutes", "can_join",
        ]

    def get_organizer_name(self, obj):
        user = obj.formation.instructor
        return user.get_full_name() or user.username

    def get_can_join(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated or obj.completed or obj.ended_at:
            return False
        user = request.user
        if _is_manager(user, obj.formation):
            return True
        # Les apprenants/invités ne rejoignent qu'une séance réellement démarrée ; cela évite
        # de comptabiliser le temps d'attente comme temps de présence pédagogique.
        if not obj.started_at:
            return False
        if obj.formation_id in self.context.get("enrolled_formation_ids", set()):
            return True
        email = (getattr(user, "email", "") or "").strip()
        return bool(email and FormationSessionInvite.objects.filter(
            session=obj, email__iexact=email, revoked_at__isnull=True
        ).exists())


class FormationSessionWriteSerializer(serializers.ModelSerializer):
    duration_minutes = serializers.IntegerField(required=False, min_value=15, max_value=480)

    class Meta:
        model = FormationSession
        fields = [
            "id", "formation", "session_number", "scheduled_at",
            "duration_minutes", "completed", "notes",
        ]
        read_only_fields = ["id", "completed"]

    def validate_formation(self, formation):
        if not _is_manager(self.context["request"].user, formation):
            raise serializers.ValidationError("Vous ne pouvez planifier que vos propres formations.")
        return formation

    def validate(self, attrs):
        formation = attrs.get("formation") or getattr(self.instance, "formation", None)
        number = attrs.get("session_number", getattr(self.instance, "session_number", None))
        if formation and number and number > formation.num_sessions:
            raise serializers.ValidationError({
                "session_number": f"Cette formation prévoit {formation.num_sessions} séance(s) au maximum."
            })

        # Une séance déjà démarrée constitue un historique pédagogique : on peut encore
        # modifier ses notes, mais plus son horaire, sa durée ou son numéro.
        if self.instance and (self.instance.started_at or self.instance.ended_at or self.instance.completed):
            protected = {"scheduled_at", "duration_minutes", "session_number", "formation"}
            if protected.intersection(attrs.keys()):
                raise serializers.ValidationError(
                    "Le planning d'une séance déjà démarrée ou terminée ne peut plus être modifié."
                )
        return attrs

    def create(self, validated_data):
        formation = validated_data["formation"]
        validated_data.setdefault("duration_minutes", formation.session_duration_minutes)
        validated_data["meeting_link"] = ""
        instance = super().create(validated_data)
        formation.sync_schedule_dates()
        return instance

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        instance.formation.sync_schedule_dates()
        return instance


class InteractiveFormationListSerializer(serializers.ModelSerializer):
    instructor = UserPublicCompactSerializer(read_only=True)
    co_instructor = UserPublicCompactSerializer(read_only=True)
    category = CategoryCompactSerializer(read_only=True)
    students_count = serializers.ReadOnlyField()
    seats_left = serializers.ReadOnlyField()
    is_full = serializers.ReadOnlyField()
    thumbnail = RelativeImageField(read_only=True)

    class Meta:
        model = InteractiveFormation
        fields = [
            "id", "title", "slug", "category", "instructor", "co_instructor",
            "level", "language", "price", "num_sessions", "session_duration_minutes",
            "max_students", "thumbnail", "start_date", "end_date", "status",
            "published", "students_count", "seats_left", "is_full", "is_enrollment_open",
            "cohort_name", "cohort_timezone", "enrollment_deadline", "min_students", "created_at",
        ]


class InteractiveFormationDetailSerializer(InteractiveFormationListSerializer):
    sessions = FormationSessionSerializer(many=True, read_only=True)
    is_enrolled = serializers.SerializerMethodField()

    class Meta(InteractiveFormationListSerializer.Meta):
        fields = InteractiveFormationListSerializer.Meta.fields + [
            "description", "sessions", "is_enrolled", "certificate_enabled", "certificate_auto_issue",
            "certificate_attendance_percent", "certificate_validity_months", "certificate_title",
            "certificate_subtitle", "certificate_description", "certificate_signatory_name",
            "certificate_signatory_title", "certificate_accent_color", "certificate_number_prefix",
            "certificate_show_duration", "certificate_show_instructor", "certificate_show_completion_date",
        ]

    def get_is_enrolled(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        if _is_manager(request.user, obj):
            return True
        return obj.id in self.context.get("enrolled_formation_ids", set())

    def to_representation(self, instance):
        self.fields["sessions"].child.context.update(self.context)
        return super().to_representation(instance)


class InteractiveFormationWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = InteractiveFormation
        fields = [
            "id", "category", "co_instructor", "title", "description", "level", "language",
            "price", "num_sessions", "session_duration_minutes", "max_students",
            "thumbnail", "start_date", "end_date", "status", "published", "slug",
            "cohort_name", "cohort_timezone", "enrollment_deadline", "min_students",
            "certificate_enabled", "certificate_auto_issue", "certificate_attendance_percent",
            "certificate_validity_months", "certificate_title", "certificate_subtitle",
            "certificate_description", "certificate_signatory_name", "certificate_signatory_title",
            "certificate_accent_color", "certificate_number_prefix", "certificate_show_duration",
            "certificate_show_instructor", "certificate_show_completion_date",
        ]
        read_only_fields = ["id", "slug"]

    def validate_certificate_attendance_percent(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("Le seuil de présence doit être compris entre 0 et 100 %.")
        return value

    def validate_cohort_timezone(self, value):
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
        value = (value or "").strip()
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise serializers.ValidationError("Fuseau horaire IANA invalide (ex. Africa/Abidjan).")
        return value

    def validate(self, attrs):
        thumbnail = attrs.get("thumbnail")
        if thumbnail:
            validate_upload_limits(
                thumbnail,
                max_bytes=settings.MAX_IMAGE_UPLOAD_MB * 1024 * 1024,
                extensions={".jpg", ".jpeg", ".png", ".webp", ".avif"},
                field="thumbnail",
            )
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end < start:
            raise serializers.ValidationError({"end_date": "La date de fin doit être postérieure à la date de début."})
        deadline = attrs.get("enrollment_deadline", getattr(self.instance, "enrollment_deadline", None))
        if deadline and start and deadline.date() > start:
            raise serializers.ValidationError({"enrollment_deadline": "La clôture des inscriptions doit être au plus tard le jour de début."})
        min_students = attrs.get("min_students", getattr(self.instance, "min_students", 1))
        max_students = attrs.get("max_students", getattr(self.instance, "max_students", 1))
        if min_students and max_students and int(min_students) > int(max_students):
            raise serializers.ValidationError({"min_students": "Le minimum d'apprenants ne peut pas dépasser le nombre de places."})
        price = attrs.get("price", getattr(self.instance, "price", 0))
        if price is not None and price < 0:
            raise serializers.ValidationError({"price": "Le prix ne peut pas être négatif."})
        co = attrs.get("co_instructor", getattr(self.instance, "co_instructor", None))
        request = self.context.get("request")
        if co:
            if co.role not in ("instructor", "admin") or not co.is_active:
                raise serializers.ValidationError({"co_instructor": "Le co-instructeur doit être un instructeur actif."})
            if request and co.id == request.user.id:
                raise serializers.ValidationError({"co_instructor": "Choisissez un autre co-instructeur."})
        return attrs

    def create(self, validated_data):
        from apps.enrollments.certificates import apply_platform_certificate_defaults
        formation = InteractiveFormation(instructor=self.context["request"].user)
        apply_platform_certificate_defaults(formation, "formation")
        for key, value in validated_data.items():
            setattr(formation, key, value)
        formation.save()
        return formation


class FormationEnrollmentSerializer(serializers.ModelSerializer):
    formation = InteractiveFormationListSerializer(read_only=True)

    class Meta:
        model = FormationEnrollment
        fields = ["id", "formation", "enrolled_at", "certificate_issued"]


class AttendanceSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = FormationAttendance
        fields = ["id", "user_id", "full_name", "role", "joined_at", "last_seen_at", "left_at", "duration_seconds", "hand_raised"]

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

class MentorshipSlotSerializer(serializers.ModelSerializer):
    is_available = serializers.SerializerMethodField()
    duration_minutes = serializers.IntegerField(source="offering.duration_minutes", read_only=True)

    class Meta:
        model = MentorshipSlot
        fields = ["id", "offering", "starts_at", "duration_minutes", "is_active", "is_available", "session"]
        read_only_fields = ["id", "session", "is_available", "duration_minutes"]

    def get_is_available(self, obj):
        from django.db.models import Q
        from django.utils import timezone
        from datetime import timedelta

        now = timezone.now()
        prefetched = getattr(obj, "_prefetched_objects_cache", {}).get("bookings")
        if prefetched is not None:
            bookings = list(prefetched)
            confirmed_exists = any(booking.status == MentorshipBooking.Status.CONFIRMED for booking in bookings)
            pending_exists = False
            for booking in bookings:
                if booking.status != MentorshipBooking.Status.PENDING_PAYMENT:
                    continue
                order_alive = any(
                    item.order.status in ("pending", "paid")
                    for item in booking.order_items.all()
                )
                if booking.expires_at is None or booking.expires_at > now or order_alive:
                    pending_exists = True
                    break
        else:
            confirmed_exists = obj.bookings.filter(status=MentorshipBooking.Status.CONFIRMED).exists()
            pending_exists = obj.bookings.filter(status=MentorshipBooking.Status.PENDING_PAYMENT).filter(
                Q(expires_at__isnull=True)
                | Q(expires_at__gt=now)
                | Q(order_items__order__status__in=["pending", "paid"])
            ).exists()
        notice = timedelta(hours=obj.offering.booking_notice_hours)
        return bool(obj.is_active and obj.starts_at > now + notice and not confirmed_exists and not pending_exists)


class MentorshipOfferingListSerializer(serializers.ModelSerializer):
    instructor = UserPublicCompactSerializer(read_only=True)
    next_slots = serializers.SerializerMethodField()

    class Meta:
        model = MentorshipOffering
        fields = [
            "id", "title", "slug", "description", "instructor", "duration_minutes", "price",
            "language", "timezone", "booking_notice_hours", "cancellation_notice_hours",
            "published", "next_slots", "created_at",
        ]

    def get_next_slots(self, obj):
        from django.utils import timezone
        view = self.context.get("view")
        now = timezone.now()
        prefetched = getattr(obj, "_prefetched_objects_cache", {}).get("slots")
        # L'espace mentor voit aussi ses créneaux désactivés / déjà réservés pour pouvoir
        # gérer leur état sans perdre l'historique. Le catalogue public reste limité aux actifs.
        if prefetched is not None:
            slots = sorted((slot for slot in prefetched if slot.starts_at > now), key=lambda slot: slot.starts_at)
            if getattr(view, "action", "") == "mine":
                slots = slots[:50]
            else:
                slots = [slot for slot in slots if slot.is_active][:12]
        else:
            qs = obj.slots.filter(starts_at__gt=now).order_by("starts_at")
            slots = qs[:50] if getattr(view, "action", "") == "mine" else qs.filter(is_active=True)[:12]
        return MentorshipSlotSerializer(slots, many=True, context=self.context).data


class MentorshipOfferingWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = MentorshipOffering
        fields = [
            "id", "title", "slug", "description", "duration_minutes", "price", "language", "timezone",
            "booking_notice_hours", "cancellation_notice_hours", "published",
        ]
        read_only_fields = ["id", "slug"]

    def validate_duration_minutes(self, value):
        if value < 15 or value > 180:
            raise serializers.ValidationError("La durée doit être comprise entre 15 et 180 minutes.")
        return value

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Le prix ne peut pas être négatif.")
        return value

    def validate_timezone(self, value):
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
        value = (value or "").strip()
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise serializers.ValidationError("Fuseau horaire IANA invalide (ex. Africa/Abidjan).")
        return value


class MentorshipBookingSerializer(serializers.ModelSerializer):
    offering = MentorshipOfferingListSerializer(read_only=True)
    slot = MentorshipSlotSerializer(read_only=True)
    join_session_id = serializers.ReadOnlyField()
    mentor_name = serializers.SerializerMethodField()
    learner_name = serializers.SerializerMethodField()

    class Meta:
        model = MentorshipBooking
        fields = [
            "id", "offering", "slot", "status", "price_snapshot", "expires_at", "confirmed_at",
            "cancelled_at", "learner_note", "mentor_note", "created_at", "updated_at",
            "join_session_id", "mentor_name", "learner_name",
        ]
        read_only_fields = [
            "id", "status", "price_snapshot", "expires_at", "confirmed_at", "cancelled_at",
            "mentor_note", "created_at", "updated_at", "join_session_id",
        ]

    def get_mentor_name(self, obj):
        u = obj.offering.instructor
        return u.get_full_name() or u.username

    def get_learner_name(self, obj):
        u = obj.user
        return u.get_full_name() or u.username

