from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from rest_framework import serializers
from apps.accounts.serializers import UserPublicCompactSerializer
from apps.catalog.serializers import CategoryCompactSerializer
from apps.common.fields import RelativeImageField
from apps.common.media_metadata import validate_upload_limits
from .models import (
    InteractiveFormation, FormationSession, FormationEnrollment, FormationAttendance, FormationSessionInvite,
    FormationWaitlistEntry, MentorshipOffering, MentorshipSlot, MentorshipBooking,
    MentorshipPack, MentorshipPass, MentorshipAvailabilityRule,
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
    waitlist_count = serializers.SerializerMethodField()
    waitlist_offered_count = serializers.SerializerMethodField()
    thumbnail = RelativeImageField(read_only=True)

    class Meta:
        model = InteractiveFormation
        fields = [
            "id", "title", "slug", "category", "instructor", "co_instructor",
            "level", "language", "price", "num_sessions", "session_duration_minutes",
            "max_students", "thumbnail", "start_date", "end_date", "status",
            "published", "students_count", "seats_left", "is_full", "is_enrollment_open", "is_waitlist_open",
            "waitlist_count", "waitlist_offered_count",
            "cohort_name", "cohort_timezone", "enrollment_deadline", "min_students", "created_at",
        ]

    def get_waitlist_count(self, obj):
        annotated = getattr(obj, "_waitlist_count", None)
        if annotated is not None:
            return int(annotated)
        return obj.waitlist_entries.filter(status=FormationWaitlistEntry.Status.WAITING).count()

    def get_waitlist_offered_count(self, obj):
        annotated = getattr(obj, "_waitlist_offered_count", None)
        if annotated is not None:
            return int(annotated)
        return obj.waitlist_entries.filter(
            status=FormationWaitlistEntry.Status.OFFERED, offer_expires_at__gt=timezone.now()
        ).count()


class InteractiveFormationDetailSerializer(InteractiveFormationListSerializer):
    sessions = FormationSessionSerializer(many=True, read_only=True)
    is_enrolled = serializers.SerializerMethodField()
    waitlist_status = serializers.SerializerMethodField()
    waitlist_position = serializers.SerializerMethodField()
    waitlist_offer_expires_at = serializers.SerializerMethodField()
    can_checkout = serializers.SerializerMethodField()
    effective_seats_left = serializers.SerializerMethodField()

    class Meta(InteractiveFormationListSerializer.Meta):
        fields = InteractiveFormationListSerializer.Meta.fields + [
            "description", "sessions", "is_enrolled", "waitlist_status", "waitlist_position", "waitlist_offer_expires_at", "can_checkout", "effective_seats_left", "certificate_enabled", "certificate_auto_issue",
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

    def _waitlist_snapshot(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated or _is_manager(request.user, obj):
            return {"status": "", "position": None, "offer_expires_at": None}
        cache = self.context.setdefault("waitlist_snapshots", {})
        if obj.id not in cache:
            from .cohorts import waitlist_snapshot
            cache[obj.id] = waitlist_snapshot(request.user, obj)
        return cache[obj.id]

    def get_waitlist_status(self, obj):
        return self._waitlist_snapshot(obj)["status"]

    def get_waitlist_position(self, obj):
        return self._waitlist_snapshot(obj)["position"]

    def get_waitlist_offer_expires_at(self, obj):
        return self._waitlist_snapshot(obj)["offer_expires_at"]

    def get_can_checkout(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            from .cohorts import effective_seats_used
            return bool(obj.is_waitlist_open and effective_seats_used(obj) < obj.max_students)
        if _is_manager(request.user, obj) or obj.id in self.context.get("enrolled_formation_ids", set()):
            return False
        from .cohorts import can_checkout_formation
        return can_checkout_formation(request.user, obj)

    def get_effective_seats_left(self, obj):
        from .cohorts import effective_seats_used
        return max(obj.max_students - effective_seats_used(obj), 0)

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
        if not (obj.is_active and obj.starts_at > now + notice and not confirmed_exists and not pending_exists):
            return False

        # Un mentor peut publier plusieurs offres. Un rendez-vous actif sur une autre
        # offre rend ce créneau indisponible s'il chevauche la même plage horaire.
        cache = self.context.setdefault("mentor_busy_bookings", {})
        instructor_id = obj.offering.instructor_id
        if instructor_id not in cache:
            cache[instructor_id] = list(
                MentorshipBooking.objects.filter(offering__instructor_id=instructor_id)
                .filter(
                    Q(status=MentorshipBooking.Status.CONFIRMED)
                    | Q(status=MentorshipBooking.Status.PENDING_PAYMENT)
                    & (
                        Q(expires_at__isnull=True)
                        | Q(expires_at__gt=now)
                        | Q(order_items__order__status__in=["pending", "paid"])
                    )
                )
                .select_related("slot", "offering")
                .distinct()
            )
        slot_end = obj.starts_at + timedelta(minutes=obj.offering.duration_minutes)
        for booking in cache[instructor_id]:
            if booking.slot_id == obj.id:
                continue
            booking_end = booking.slot.starts_at + timedelta(minutes=booking.offering.duration_minutes)
            if booking.slot.starts_at < slot_end and booking_end > obj.starts_at:
                return False
        return True


class MentorshipOfferingListSerializer(serializers.ModelSerializer):
    instructor = UserPublicCompactSerializer(read_only=True)
    next_slots = serializers.SerializerMethodField()
    packs = serializers.SerializerMethodField()

    class Meta:
        model = MentorshipOffering
        fields = [
            "id", "title", "slug", "description", "instructor", "duration_minutes", "price",
            "language", "timezone", "booking_notice_hours", "cancellation_notice_hours",
            "published", "next_slots", "packs", "created_at",
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

    def get_packs(self, obj):
        packs = obj.packs.all() if hasattr(obj, "packs") else []
        view = self.context.get("view")
        if getattr(view, "action", "") != "mine":
            packs = [p for p in packs if p.published] if isinstance(packs, list) else packs.filter(published=True)
        return MentorshipPackSerializer(packs, many=True, context=self.context).data


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


class MentorshipPackSerializer(serializers.ModelSerializer):
    effective_price_per_session = serializers.SerializerMethodField()

    class Meta:
        model = MentorshipPack
        fields = ["id", "offering", "sessions_count", "price", "validity_days", "published", "effective_price_per_session", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_effective_price_per_session(self, obj):
        if not obj.sessions_count:
            return "0.00"
        return str((obj.price / obj.sessions_count).quantize(Decimal("0.01")))

    def validate_sessions_count(self, value):
        if value < 2 or value > 20:
            raise serializers.ValidationError("Un pack doit contenir entre 2 et 20 séances.")
        return value

    def validate_validity_days(self, value):
        if value < 7 or value > 730:
            raise serializers.ValidationError("La validité doit être comprise entre 7 et 730 jours.")
        return value


class MentorshipPassSerializer(serializers.ModelSerializer):
    offering_id = serializers.IntegerField(source="pack.offering_id", read_only=True)
    offering_title = serializers.CharField(source="pack.offering.title", read_only=True)
    sessions_count = serializers.IntegerField(source="total_sessions", read_only=True)
    is_active = serializers.ReadOnlyField()

    class Meta:
        model = MentorshipPass
        fields = ["id", "pack", "offering_id", "offering_title", "sessions_count", "remaining_sessions", "expires_at", "revoked_at", "is_active", "created_at"]
        read_only_fields = fields


class MentorshipAvailabilityRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = MentorshipAvailabilityRule
        fields = ["id", "offering", "weekday", "start_time", "end_time", "interval_minutes", "valid_from", "valid_until", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        start = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end = attrs.get("end_time", getattr(self.instance, "end_time", None))
        if start and end and start >= end:
            raise serializers.ValidationError({"end_time": "L'heure de fin doit être postérieure à l'heure de début."})
        valid_from = attrs.get("valid_from", getattr(self.instance, "valid_from", None))
        valid_until = attrs.get("valid_until", getattr(self.instance, "valid_until", None))
        if valid_from and valid_until and valid_until < valid_from:
            raise serializers.ValidationError({"valid_until": "La date de fin doit être postérieure à la date de début."})
        interval = attrs.get("interval_minutes", getattr(self.instance, "interval_minutes", 60))
        if interval < 15 or interval > 240:
            raise serializers.ValidationError({"interval_minutes": "L'intervalle doit être compris entre 15 et 240 minutes."})
        offering = attrs.get("offering", getattr(self.instance, "offering", None))
        weekday = attrs.get("weekday", getattr(self.instance, "weekday", None))
        if offering and weekday is not None and start and end:
            overlaps = MentorshipAvailabilityRule.objects.filter(
                offering=offering, weekday=weekday, start_time__lt=end, end_time__gt=start
            )
            if self.instance:
                overlaps = overlaps.exclude(pk=self.instance.pk)
            if overlaps.exists():
                raise serializers.ValidationError({
                    "start_time": "Cette plage chevauche déjà une autre disponibilité récurrente de cette offre."
                })
        return attrs


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
            "cancelled_at", "learner_note", "mentor_note", "mentorship_pass", "rescheduled_at", "reschedule_count", "created_at", "updated_at",
            "join_session_id", "mentor_name", "learner_name",
        ]
        read_only_fields = [
            "id", "status", "price_snapshot", "expires_at", "confirmed_at", "cancelled_at",
            "mentor_note", "mentorship_pass", "rescheduled_at", "reschedule_count", "created_at", "updated_at", "join_session_id",
        ]

    def get_mentor_name(self, obj):
        u = obj.offering.instructor
        return u.get_full_name() or u.username

    def get_learner_name(self, obj):
        u = obj.user
        return u.get_full_name() or u.username

