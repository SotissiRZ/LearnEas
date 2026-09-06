from django.conf import settings
from django.db import transaction
from rest_framework import serializers
from apps.accounts.serializers import UserPublicCompactSerializer, UserPublicSerializer
from apps.common.fields import RelativeImageField, RelativeFileField, ProtectedFileField, sign_private_media_name
from apps.common.media_metadata import extract_pdf_page_count, validate_upload_limits
from apps.common.hls_media import sign_hls_path
from .models import Domain, Category, Course, Section, Lesson, PDFResource, PDFProduct


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


class DomainCompactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Domain
        fields = ["id", "name", "slug", "icon", "description", "order"]


class DomainSerializer(DomainCompactSerializer):
    courses_count = serializers.SerializerMethodField()

    class Meta(DomainCompactSerializer.Meta):
        fields = DomainCompactSerializer.Meta.fields + ["courses_count"]

    def get_courses_count(self, obj):
        annotated = getattr(obj, "published_courses_count", None)
        if annotated is not None:
            return annotated
        return Course.objects.filter(published=True, category__domain=obj).count()


class CategoryCompactSerializer(serializers.ModelSerializer):
    domain = DomainCompactSerializer(read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "icon", "description", "domain"]


class CategorySerializer(serializers.ModelSerializer):
    courses_count = serializers.SerializerMethodField()
    domain = DomainCompactSerializer(read_only=True)
    domain_id = serializers.PrimaryKeyRelatedField(
        source="domain", queryset=Domain.objects.all(), write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "icon", "description", "domain", "domain_id", "courses_count"]

    def get_courses_count(self, obj):
        annotated = getattr(obj, "published_courses_count", None)
        return annotated if annotated is not None else obj.courses.filter(published=True).count()


class LessonSerializer(serializers.ModelSerializer):
    locked = serializers.SerializerMethodField()
    video_file = ProtectedFileField(read_only=True)
    subtitles_file = ProtectedFileField(read_only=True)
    hls_url = serializers.SerializerMethodField()
    audio_hls_url = serializers.SerializerMethodField()
    data_saver_hls_url = serializers.SerializerMethodField()
    offline_download_url = serializers.SerializerMethodField()
    offline_progress_token = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = [
            "id", "title", "video_url", "video_file", "duration_minutes", "duration_seconds",
            "order", "is_preview", "description", "subtitles_file", "transcript", "locked",
            "hls_url", "audio_hls_url", "data_saver_hls_url", "streaming_status", "streaming_variants",
            "offline_download_allowed", "offline_download_url", "offline_progress_token", "offline_video_size_bytes",
        ]

    def get_hls_url(self, obj):
        if obj.streaming_status != "ready" or not obj.hls_master_path:
            return None
        try:
            return sign_hls_path(obj.hls_master_path)
        except Exception:
            return None

    def get_audio_hls_url(self, obj):
        if obj.streaming_status != "ready" or not obj.audio_hls_path:
            return None
        try:
            return sign_hls_path(obj.audio_hls_path)
        except Exception:
            return None

    def get_data_saver_hls_url(self, obj):
        if obj.streaming_status != "ready" or not obj.hls_master_path:
            return None
        try:
            return sign_hls_path(obj.hls_master_path, max_height=settings.HLS_DATA_SAVER_MAX_HEIGHT)
        except Exception:
            return None

    def get_offline_download_url(self, obj):
        if not obj.offline_download_allowed or not obj.offline_video_path:
            return None
        return sign_private_media_name(obj.offline_video_path)

    def get_offline_progress_token(self, obj):
        request = self.context.get("request")
        if not obj.offline_download_allowed or not obj.offline_video_path or not request or not request.user.is_authenticated:
            return None
        try:
            from django.core import signing
            from django.utils import timezone
            return signing.dumps({
                "lesson_id": obj.id,
                "user_id": request.user.id,
                "issued_at": int(timezone.now().timestamp()),
            }, salt="kalanpro.offline-progress", compress=True)
        except Exception:
            return None

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
            data["hls_url"] = None
            data["audio_hls_url"] = None
            data["data_saver_hls_url"] = None
            data["offline_download_url"] = None
            data["offline_progress_token"] = None
            data["offline_download_allowed"] = False
            data["offline_video_size_bytes"] = 0
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
    instructor = UserPublicCompactSerializer(read_only=True)
    category = CategoryCompactSerializer(read_only=True)
    effective_price = serializers.SerializerMethodField()
    thumbnail = RelativeImageField(read_only=True)

    class Meta:
        model = Course
        fields = [
            "id", "title", "slug", "subtitle", "category", "instructor",
            "level", "language", "price", "discount_price", "effective_price",
            "is_free", "premium_included", "thumbnail", "total_duration_minutes", "total_hours",
            "total_lessons", "students_count", "rating_avg", "rating_count",
            "featured", "published", "created_at",
        ]

    def get_effective_price(self, obj):
        if obj.is_free:
            return 0
        return obj.discount_price if obj.discount_price else obj.price


class CourseDetailSerializer(CourseListSerializer):
    instructor = UserPublicSerializer(read_only=True)
    sections = SectionSerializer(many=True, read_only=True)
    pdf_resources = PDFResourceSerializer(many=True, read_only=True)
    is_enrolled = serializers.SerializerMethodField()
    project_count = serializers.SerializerMethodField()
    required_project_count = serializers.SerializerMethodField()

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
            "certificate_show_completion_date", "video_completion_threshold_percent",
            "project_count", "required_project_count",
        ]

    def get_project_count(self, obj):
        return obj.project_assignments.filter(published=True).count()

    def get_required_project_count(self, obj):
        return obj.project_assignments.filter(published=True, required_for_certificate=True).count()

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
            "thumbnail", "promo_video_url", "published", "featured", "premium_included", "slug",
            "certificate_enabled", "certificate_auto_issue", "certificate_threshold_percent",
            "certificate_validity_months", "certificate_title", "certificate_subtitle",
            "certificate_description", "certificate_signatory_name", "certificate_signatory_title",
            "certificate_accent_color", "certificate_number_prefix", "certificate_show_duration",
            "certificate_show_instructor", "certificate_show_completion_date",
            "video_completion_threshold_percent",
        ]
        read_only_fields = ["id", "slug"]

    def validate(self, attrs):
        request = self.context.get("request")
        price = attrs.get("price", getattr(self.instance, "price", 0))
        discount = attrs.get("discount_price", getattr(self.instance, "discount_price", None))
        is_free = attrs.get("is_free", getattr(self.instance, "is_free", False))
        if price is not None and price < 0:
            raise serializers.ValidationError({"price": "Le prix ne peut pas être négatif."})
        if discount is not None and (discount < 0 or (price is not None and discount >= price)):
            raise serializers.ValidationError({"discount_price": "Le prix promotionnel doit être positif et inférieur au prix normal."})
        if is_free:
            attrs["price"] = 0
            attrs["discount_price"] = None
        thumbnail = attrs.get("thumbnail")
        if thumbnail:
            validate_upload_limits(thumbnail, max_bytes=settings.MAX_IMAGE_UPLOAD_MB * 1024 * 1024, extensions={".jpg", ".jpeg", ".png", ".webp", ".avif"}, field="thumbnail")
        # `featured` est une décision éditoriale de l'administrateur. Le frontend peut
        # néanmoins envoyer `featured=false` avec un formulaire générique : on l'ignore.
        if request and request.user.role != "admin":
            attrs.pop("featured", None)
            attrs.pop("premium_included", None)
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
            "subtitles_file", "transcript", "offline_download_allowed",
        ]

    def validate_section(self, section):
        _validate_owner(self.context["request"], section.course.instructor_id, "section")
        return section

    def validate(self, attrs):
        subtitles_file = attrs.get("subtitles_file")
        if subtitles_file:
            validate_upload_limits(subtitles_file, max_bytes=5 * 1024 * 1024, extensions={".vtt"}, field="subtitles_file")
        video_file = attrs.get("video_file")
        if video_file:
            # Validation légère uniquement pendant la requête HTTP. Aucun ffprobe/ffmpeg ici :
            # les fichiers volumineux doivent être sauvegardés rapidement puis traités par Celery.
            validate_upload_limits(video_file, max_bytes=settings.MAX_VIDEO_UPLOAD_MB * 1024 * 1024, extensions={".mp4", ".webm", ".mov", ".m4v"}, field="video_file")
        video_url = attrs.get("video_url")
        if self.instance:
            video_file = video_file or self.instance.video_file
            video_url = video_url if "video_url" in attrs else self.instance.video_url
        if not video_file and not video_url:
            raise serializers.ValidationError({"video_file": "Ajoutez un fichier vidéo ou une URL vidéo."})
        if attrs.get("video_file"):
            # La durée réelle est calculée dans normalize_lesson_video après sauvegarde.
            # Ne jamais lancer ffprobe sur le chemin critique d'un upload de plusieurs Go.
            attrs["duration_minutes"] = 0
        elif video_url and not attrs.get("duration_minutes") and not (self.instance and self.instance.duration_minutes):
            raise serializers.ValidationError({
                "video_url": "Impossible de déterminer la durée. Vérifiez que l'URL vidéo est accessible."
            })
        return attrs

    def _schedule_video_processing(self, lesson):
        if not lesson.video_file:
            return
        from .models import StreamingStatus
        from .tasks import normalize_lesson_video
        Lesson.objects.filter(pk=lesson.pk).update(
            streaming_status=StreamingStatus.PENDING,
            streaming_error="Vidéo en attente de préparation.",
        )

        def enqueue():
            try:
                normalize_lesson_video.delay(lesson.pk)
            except Exception:
                # L'upload reste valide même si Redis/Celery est momentanément indisponible.
                # L'instructeur peut relancer la préparation depuis l'interface.
                Lesson.objects.filter(pk=lesson.pk).update(
                    streaming_status=StreamingStatus.PENDING,
                    streaming_error="Worker vidéo temporairement indisponible.",
                )

        transaction.on_commit(enqueue)

    def create(self, validated_data):
        lesson = super().create(validated_data)
        if lesson.video_file:
            self._schedule_video_processing(lesson)
        return lesson

    def update(self, instance, validated_data):
        video_changed = "video_file" in validated_data
        offline_changed = "offline_download_allowed" in validated_data and bool(validated_data["offline_download_allowed"]) != bool(instance.offline_download_allowed)
        old_offline_path = instance.offline_video_path
        lesson = super().update(instance, validated_data)
        if video_changed and lesson.video_file:
            self._schedule_video_processing(lesson)
        elif offline_changed and lesson.video_file:
            if lesson.offline_download_allowed:
                from .tasks import prepare_lesson_streaming
                transaction.on_commit(lambda: prepare_lesson_streaming.delay(lesson.pk, force=True))
            else:
                if old_offline_path:
                    try:
                        from django.core.files.storage import default_storage
                        default_storage.delete(old_offline_path)
                    except Exception:
                        pass
                Lesson.objects.filter(pk=lesson.pk).update(offline_video_path="", offline_video_size_bytes=0)
        return lesson


class LessonDirectCompleteSerializer(serializers.Serializer):
    section = serializers.PrimaryKeyRelatedField(queryset=Section.objects.select_related("course__instructor").all())
    title = serializers.CharField(max_length=200)
    order = serializers.IntegerField(required=False, min_value=0, default=1)
    is_preview = serializers.BooleanField(required=False, default=False)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    subtitles_file = serializers.FileField(required=False, allow_null=True)
    transcript = serializers.CharField(required=False, allow_blank=True, default="")
    offline_download_allowed = serializers.BooleanField(required=False, default=False)
    object_key = serializers.CharField(max_length=700)
    upload_id = serializers.CharField(max_length=1000)
    expected_size = serializers.IntegerField(min_value=1)
    parts = serializers.ListField(child=serializers.DictField(), allow_empty=False)

    def validate_section(self, section):
        _validate_owner(self.context["request"], section.course.instructor_id, "section")
        return section

    def validate_subtitles_file(self, value):
        if value:
            validate_upload_limits(value, max_bytes=5 * 1024 * 1024, extensions={".vtt"}, field="subtitles_file")
        return value


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
            validate_upload_limits(attrs["file"], max_bytes=settings.MAX_PDF_UPLOAD_MB * 1024 * 1024, extensions={".pdf"}, field="file")
            attrs["page_count"] = extract_pdf_page_count(attrs["file"])
        if attrs.get("cover_image"):
            validate_upload_limits(attrs["cover_image"], max_bytes=settings.MAX_IMAGE_UPLOAD_MB * 1024 * 1024, extensions={".jpg", ".jpeg", ".png", ".webp", ".avif"}, field="cover_image")
        return attrs


class PDFProductListSerializer(serializers.ModelSerializer):
    instructor = UserPublicCompactSerializer(read_only=True)
    category = CategoryCompactSerializer(read_only=True)
    cover_image = RelativeImageField(read_only=True)

    class Meta:
        model = PDFProduct
        fields = [
            "id", "title", "slug", "category", "instructor", "level", "language",
            "price", "is_free", "premium_included", "cover_image", "page_count", "downloads_count",
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
            "page_count", "published", "featured", "premium_included", "slug",
        ]
        read_only_fields = ["id", "slug", "page_count"]

    def validate(self, attrs):
        if attrs.get("file"):
            validate_upload_limits(attrs["file"], max_bytes=settings.MAX_PDF_UPLOAD_MB * 1024 * 1024, extensions={".pdf"}, field="file")
            attrs["page_count"] = extract_pdf_page_count(attrs["file"])
        if attrs.get("preview_file"):
            validate_upload_limits(attrs["preview_file"], max_bytes=min(settings.MAX_PDF_UPLOAD_MB, 50) * 1024 * 1024, extensions={".pdf"}, field="preview_file")
            extract_pdf_page_count(attrs["preview_file"])
        if attrs.get("cover_image"):
            validate_upload_limits(attrs["cover_image"], max_bytes=settings.MAX_IMAGE_UPLOAD_MB * 1024 * 1024, extensions={".jpg", ".jpeg", ".png", ".webp", ".avif"}, field="cover_image")
        price = attrs.get("price", getattr(self.instance, "price", 0))
        is_free = attrs.get("is_free", getattr(self.instance, "is_free", False))
        if price is not None and price < 0:
            raise serializers.ValidationError({"price": "Le prix ne peut pas être négatif."})
        if is_free:
            attrs["price"] = 0
        request = self.context.get("request")
        if request and request.user.role != "admin":
            attrs.pop("featured", None)
            attrs.pop("premium_included", None)
        return attrs

    def create(self, validated_data):
        validated_data["instructor"] = self.context["request"].user
        return super().create(validated_data)
