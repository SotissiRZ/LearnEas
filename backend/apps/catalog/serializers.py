from rest_framework import serializers
from apps.accounts.serializers import UserPublicSerializer
from apps.common.fields import RelativeImageField, RelativeFileField
from .models import Category, Course, Section, Lesson, PDFResource, PDFProduct


class CategorySerializer(serializers.ModelSerializer):
    courses_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "icon", "description", "courses_count"]

    def get_courses_count(self, obj):
        return obj.courses.filter(published=True).count()


class LessonSerializer(serializers.ModelSerializer):
    locked = serializers.SerializerMethodField()
    video_file = RelativeFileField(read_only=True)

    class Meta:
        model = Lesson
        fields = [
            "id", "title", "video_url", "video_file", "duration_minutes",
            "order", "is_preview", "description", "locked",
        ]

    def get_locked(self, obj):
        """La vidéo n'est renvoyée en clair que si preview ou utilisateur inscrit."""
        request = self.context.get("request")
        if obj.is_preview:
            return False
        enrolled = self.context.get("enrolled_course_ids", set())
        return obj.section.course_id not in enrolled

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data["locked"]:
            data["video_url"] = None
            data["video_file"] = None
        return data


class SectionSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True)
    duration_minutes = serializers.ReadOnlyField()

    class Meta:
        model = Section
        fields = ["id", "title", "order", "duration_minutes", "lessons"]


class PDFResourceSerializer(serializers.ModelSerializer):
    locked = serializers.SerializerMethodField()
    file = RelativeFileField(read_only=True)

    class Meta:
        model = PDFResource
        fields = ["id", "title", "file", "page_count", "is_free_sample", "order", "locked"]

    def get_locked(self, obj):
        if obj.is_free_sample:
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
            "is_enrolled",
        ]

    def get_is_enrolled(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.id in self.context.get("enrolled_course_ids", set())

    def to_representation(self, instance):
        # propage le contexte (utilisateur/inscriptions) vers les sous-serializers
        self.fields["sections"].child.fields["lessons"].child.context.update(self.context)
        return super().to_representation(instance)


class CourseWriteSerializer(serializers.ModelSerializer):
    """Création / édition d'un cours par un instructeur."""

    class Meta:
        model = Course
        fields = [
            "id", "category", "title", "subtitle", "description",
            "what_you_will_learn", "requirements", "target_audience",
            "level", "language", "price", "is_free", "discount_price",
            "thumbnail", "promo_video_url", "published", "slug",
        ]
        read_only_fields = ["id", "slug"]

    def create(self, validated_data):
        validated_data["instructor"] = self.context["request"].user
        return super().create(validated_data)


class SectionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ["id", "course", "title", "order"]


class LessonWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = [
            "id", "section", "title", "video_url", "video_file",
            "duration_minutes", "order", "is_preview", "description",
        ]


class PDFResourceWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PDFResource
        fields = ["id", "course", "title", "file", "page_count", "is_free_sample", "order"]


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
    file = RelativeFileField(read_only=True)
    preview_file = RelativeFileField(read_only=True)

    class Meta(PDFProductListSerializer.Meta):
        fields = PDFProductListSerializer.Meta.fields + ["description", "file", "preview_file", "is_purchased"]

    def get_is_purchased(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.id in self.context.get("purchased_pdf_ids", set())

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not data["is_purchased"] and not instance.is_free:
            data["file"] = None
        return data


class PDFProductWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PDFProduct
        fields = [
            "id", "category", "title", "description", "level", "language",
            "price", "is_free", "cover_image", "file", "preview_file",
            "page_count", "published", "slug",
        ]
        read_only_fields = ["id", "slug"]

    def create(self, validated_data):
        validated_data["instructor"] = self.context["request"].user
        return super().create(validated_data)
