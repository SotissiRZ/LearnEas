from rest_framework import serializers
from apps.accounts.serializers import UserPublicSerializer
from apps.catalog.serializers import CategorySerializer
from .models import InteractiveFormation, FormationSession, FormationEnrollment


class FormationSessionSerializer(serializers.ModelSerializer):
    meeting_link = serializers.SerializerMethodField()

    class Meta:
        model = FormationSession
        fields = [
            "id", "session_number", "scheduled_at", "duration_minutes",
            "meeting_link", "completed", "notes",
        ]

    def get_meeting_link(self, obj):
        """Le lien de réunion n'est visible que par les inscrits (et l'instructeur)."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        user = request.user
        if user == obj.formation.instructor or user == obj.formation.co_instructor or user.role == "admin":
            return obj.meeting_link
        if obj.formation_id in self.context.get("enrolled_formation_ids", set()):
            return obj.meeting_link
        return None


class FormationSessionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormationSession
        fields = [
            "id", "formation", "session_number", "scheduled_at",
            "duration_minutes", "meeting_link", "completed", "notes",
        ]


class InteractiveFormationListSerializer(serializers.ModelSerializer):
    instructor = UserPublicSerializer(read_only=True)
    co_instructor = UserPublicSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    students_count = serializers.ReadOnlyField()
    seats_left = serializers.ReadOnlyField()
    is_full = serializers.ReadOnlyField()

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
        fields = InteractiveFormationListSerializer.Meta.fields + ["description", "sessions", "is_enrolled"]

    def get_is_enrolled(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
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
        ]
        read_only_fields = ["id", "slug"]

    def create(self, validated_data):
        validated_data["instructor"] = self.context["request"].user
        return super().create(validated_data)


class FormationEnrollmentSerializer(serializers.ModelSerializer):
    formation = InteractiveFormationListSerializer(read_only=True)

    class Meta:
        model = FormationEnrollment
        fields = ["id", "formation", "enrolled_at", "certificate_issued"]
