from rest_framework import serializers
from apps.accounts.serializers import UserPublicSerializer
from apps.catalog.serializers import CategorySerializer
from apps.common.fields import RelativeImageField
from .models import InteractiveFormation, FormationSession, FormationEnrollment, FormationAttendance


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
        # Les apprenants ne rejoignent qu'une séance réellement démarrée ; cela évite
        # de comptabiliser le temps d'attente comme temps de présence pédagogique.
        return bool(obj.started_at and obj.formation_id in self.context.get("enrolled_formation_ids", set()))


class FormationSessionWriteSerializer(serializers.ModelSerializer):
    duration_minutes = serializers.IntegerField(read_only=True)

    class Meta:
        model = FormationSession
        fields = [
            "id", "formation", "session_number", "scheduled_at",
            "duration_minutes", "completed", "notes",
        ]
        read_only_fields = ["id", "duration_minutes"]

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
        return attrs

    def create(self, validated_data):
        formation = validated_data["formation"]
        validated_data["duration_minutes"] = formation.session_duration_minutes
        validated_data["meeting_link"] = ""
        return super().create(validated_data)


class InteractiveFormationListSerializer(serializers.ModelSerializer):
    instructor = UserPublicSerializer(read_only=True)
    co_instructor = UserPublicSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
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
            "published", "students_count", "seats_left", "is_full", "created_at",
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
