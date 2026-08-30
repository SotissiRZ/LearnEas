from rest_framework import serializers
from apps.accounts.serializers import UserPublicSerializer
from apps.common.fields import RelativeImageField, RelativeFileField, ProtectedFileField
from apps.common.media_metadata import extract_pdf_page_count, extract_video_duration_minutes
from .models import Category, Course, Section, Lesson, PDFResource, PDFProduct


def _is_admin(user) -> bool:
    return bool(user and user.is_authenticated and user.role == "admin")


def _can_manage_course(request, course: Course) -> bool:
    if not request or not request.user.is_authenticated:
        return False
    return _is_admin(request.user) or course.instructor_id == request.user.id


def _can_manage_pdf(request, pdf: PDFProduct) -> bool:
    if not request or not request.user.is_authenticated:
        return False
    return _is_admin(request.user) or pdf.instructor_id == request.user.id


def _validate_owner(request, owner_id: int, field_name: str):
    user = request.user
    if user.role != "admin" and user.id != owner_id:
        raise serializers.ValidationError({field_name: "Vous ne pouvez modifier que votre propre contenu."})


class CategorySerializer(serializers.ModelSerializer):
    courses_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "icon", "description", "courses_count"]

    def get_courses_count(self, obj):
        return obj.courses.filter(published=True).count()


class LessonSerializer(serializers.ModelSerializer):
    locked = serializers.SerializerMethodField()
    video_file = ProtectedFileField(read_only=True)
    subtitles_file = ProtectedFileField(read_only=True)

    class Meta:
        model = Lesson
        fields = [
            "id", "title", "video_url", "video_file", "duration_minutes",
            "order", "is_preview", "description", "subtitles_file", "transcript", "locked",
        ]

    def get_locked(self, obj):
        """Débloque previews, achats valides et contenu appartenant à l'organisateur/admin."""
        request = self.context.get("request")
        if obj.is_preview or _can_manage_course(request, obj.section.course):
            return False
        enrolled = self.context.get("enrolled_course_ids", set())
        return obj.section.course_id not in enrolled

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data["locked"]:
            data["video_url"] = None
            data["video_file"] = None
            data["subtitles_file"] = None
            data["transcript"] = ""
        return data


class SectionSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True)
    duration_minutes = serializers.ReadOnlyField()

    class Meta:
        model = Section
        fields = ["id", "title", "order", "duration_minutes", "lessons"]


class PDFResourceSerializer(serializers.ModelSerializer):
    locked = serializers.SerializerMethodField()
    file = ProtectedFileField(read_only=True)
    cover_image = RelativeImageField(read_only=True)

    class Meta:
        model = PDFResource
        fields = ["id", "title", "cover_image", "file", "page_count", "is_free_sample", "order", "locked"]

    def get_locked(self, obj):
        request = self.context.get("request")
        if obj.is_free_sample or _can_manage_course(request, obj.course):
            return False
        enrolled = self.context.get("enrolled_course_ids", set())
        return obj.course_id not in enrolled

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data["locked"]:
            data["file"] = None
        return data


class CourseListSerializer(serializers.ModelSerializer):
    """Vue catalogue / cartes cours (style Udemy)."""
    instructor = UserPublicSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    effective_price = serializers.SerializerMethodField()
    thumbnail = RelativeImageField(read_only=True)

    class Meta:
        model = Course
        fields = [
            "id", "title", "slug", "subtitle", "category", "instructor",
            "level", "language", "price", "discount_price", "effective_price",
            "is_free", "thumbnail", "total_duration_minutes", "total_hours",
            "total_lessons", "students_count", "rating_avg", "rating_count",
            "featured", "published", "created_at",
        ]

    def get_effective_price(self, obj):
        if obj.is_free:
            return 0
        return obj.discount_price if obj.discount_price else obj.price


class CourseDetailSerializer(CourseListSerializer):
    sections = SectionSerializer(many=True, read_only=True)
    pdf_resources = PDFResourceSerializer(many=True, read_only=True)
    is_enrolled = serializers.SerializerMethodField()

    class Meta(CourseListSerializer.Meta):
        fields = CourseListSerializer.Meta.fields + [
            "description", "what_you_will_learn", "requirements",
            "target_audience", "promo_video_url", "sections", "pdf_resources",
            "is_enrolled", "certificate_enabled", "certificate_auto_issue",
            "certificate_threshold_percent", "certificate_validity_months",
            "certificate_title", "certificate_subtitle", "certificate_description",
            "certificate_signatory_name", "certificate_signatory_title",
            "certificate_accent_color", "certificate_number_prefix",
            "certificate_show_duration", "certificate_show_instructor",
            "certificate_show_completion_date",
        ]

    def get_is_enrolled(self, obj):
        request = self.context.get("request")
        if _can_manage_course(request, obj):
            return True
        if not request or not request.user.is_authenticated:
            return False
        return obj.id in self.context.get("enrolled_course_ids", set())

    def to_representation(self, instance):
        # Propage explicitement le contexte d'accès vers tous les sous-serializers.
        self.fields["sections"].child.fields["lessons"].child.context.update(self.context)
        self.fields["pdf_resources"].child.context.update(self.context)
        return super().to_representation(instance)


class CourseWriteSerializer(serializers.ModelSerializer):
    """Création / édition d'un cours par un instructeur."""

    class Meta:
        model = Course
        fields = [
            "id", "category", "title", "subtitle", "description",
            "what_you_will_learn", "requirements", "target_audience",
            "level", "language", "price", "is_free", "discount_price",
            "thumbnail", "promo_video_url", "published", "featured", "slug",
            "certificate_enabled", "certificate_auto_issue", "certificate_threshold_percent",
            "certificate_validity_months", "certificate_title", "certificate_subtitle",
            "certificate_description", "certificate_signatory_name", "certificate_signatory_title",
            "certificate_accent_color", "certificate_number_prefix", "certificate_show_duration",
            "certificate_show_instructor", "certificate_show_completion_date",
        ]
        read_only_fields = ["id", "slug"]

    def validate(self, attrs):
        request = self.context.get("request")
        if request and request.user.role != "admin" and "featured" in attrs:
            raise serializers.ValidationError({"featured": "Seul un administrateur peut mettre un cours en avant."})
        return attrs

    def validate_certificate_threshold_percent(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("Le seuil doit être compris entre 0 et 100 %.")
        return value

    def create(self, validated_data):
        from apps.enrollments.certificates import apply_platform_certificate_defaults
        course = Course(instructor=self.context["request"].user)
        apply_platform_certificate_defaults(course, "course")
        for key, value in validated_data.items():
            setattr(course, key, value)
        course.save()
        return course


class SectionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ["id", "course", "title", "order"]

    def validate_course(self, course):
        _validate_owner(self.context["request"], course.instructor_id, "course")
        return course


class LessonWriteSerializer(serializers.ModelSerializer):
    # Pour un upload, la valeur est écrasée par la durée calculée. Pour une URL vidéo héritée,
    # le front la calcule automatiquement via les métadonnées HTML5 et l'envoie sans saisie utilisateur.
    duration_minutes = serializers.IntegerField(required=False, min_value=1)

    class Meta:
        model = Lesson
        fields = [
            "id", "section", "title", "video_url", "video_file",
            "duration_minutes", "order", "is_preview", "description",
            "subtitles_file", "transcript",
        ]

    def validate_section(self, section):
        _validate_owner(self.context["request"], section.course.instructor_id, "section")
        return section

    def validate(self, attrs):
        subtitles_file = attrs.get("subtitles_file")
        if subtitles_file and not subtitles_file.name.lower().endswith(".vtt"):
            raise serializers.ValidationError({"subtitles_file": "Le fichier de sous-titres doit être au format WebVTT (.vtt)."})
        video_file = attrs.get("video_file")
        video_url = attrs.get("video_url")
        if self.instance:
            video_file = video_file or self.instance.video_file
            video_url = video_url if "video_url" in attrs else self.instance.video_url
        if not video_file and not video_url:
            raise serializers.ValidationError({"video_file": "Ajoutez un fichier vidéo ou une URL vidéo."})
        if attrs.get("video_file"):
            attrs["duration_minutes"] = extract_video_duration_minutes(attrs["video_file"])
        elif video_url and not attrs.get("duration_minutes") and not (self.instance and self.instance.duration_minutes):
            raise serializers.ValidationError({
                "video_url": "Impossible de déterminer la durée. Vérifiez que l'URL vidéo est accessible."
            })
        return attrs


class PDFResourceWriteSerializer(serializers.ModelSerializer):
    page_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = PDFResource
        fields = ["id", "course", "title", "cover_image", "file", "page_count", "is_free_sample", "order"]

    def validate_course(self, course):
        _validate_owner(self.context["request"], course.instructor_id, "course")
        return course

    def validate(self, attrs):
        if attrs.get("file"):
            attrs["page_count"] = extract_pdf_page_count(attrs["file"])
        return attrs


class PDFProductListSerializer(serializers.ModelSerializer):
    instructor = UserPublicSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    cover_image = RelativeImageField(read_only=True)

    class Meta:
        model = PDFProduct
        fields = [
            "id", "title", "slug", "category", "instructor", "level", "language",
            "price", "is_free", "cover_image", "page_count", "downloads_count",
            "rating_avg", "rating_count", "featured", "published", "created_at",
        ]


class PDFProductDetailSerializer(PDFProductListSerializer):
    is_purchased = serializers.SerializerMethodField()
    file = ProtectedFileField(read_only=True)
    preview_file = ProtectedFileField(read_only=True)

    class Meta(PDFProductListSerializer.Meta):
        fields = PDFProductListSerializer.Meta.fields + ["description", "file", "preview_file", "is_purchased"]

    def get_is_purchased(self, obj):
        request = self.context.get("request")
        if _can_manage_pdf(request, obj):
            return True
        if not request or not request.user.is_authenticated:
            return False
        return obj.id in self.context.get("purchased_pdf_ids", set())

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not data["is_purchased"] and not instance.is_free:
            data["file"] = None
        return data


class PDFProductWriteSerializer(serializers.ModelSerializer):
    page_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = PDFProduct
        fields = [
            "id", "category", "title", "description", "level", "language",
            "price", "is_free", "cover_image", "file", "preview_file",
            "page_count", "published", "featured", "slug",
        ]
        read_only_fields = ["id", "slug", "page_count"]

    def validate(self, attrs):
        if attrs.get("file"):
            attrs["page_count"] = extract_pdf_page_count(attrs["file"])
        request = self.context.get("request")
        if request and request.user.role != "admin" and "featured" in attrs:
            raise serializers.ValidationError({"featured": "Seul un administrateur peut mettre un PDF en avant."})
        return attrs

    def create(self, validated_data):
        validated_data["instructor"] = self.context["request"].user
        return super().create(validated_data)
