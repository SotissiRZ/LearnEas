import json

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q
from celery.result import AsyncResult
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.enrollments.models import CourseEnrollment, PDFPurchase
from .models import Domain, Category, Course, Section, Lesson, PDFResource, PDFProduct
from .permissions import IsInstructorOrAdmin, IsInstructorOrAdminOnly, IsAdminRoleOrReadOnly
from .tasks import normalize_lesson_video, prepare_lesson_streaming
from apps.common.hls_media import sign_hls_path
from .serializers import (
    DomainSerializer, CategorySerializer, CourseListSerializer, CourseDetailSerializer, CourseWriteSerializer,
    SectionWriteSerializer, LessonWriteSerializer, LessonDirectCompleteSerializer, PDFResourceWriteSerializer,
    PDFProductListSerializer, PDFProductDetailSerializer, PDFProductWriteSerializer,
)


class DomainViewSet(viewsets.ModelViewSet):
    queryset = Domain.objects.annotate(
        published_courses_count=Count(
            "categories__courses",
            filter=Q(categories__courses__published=True),
            distinct=True,
        )
    )
    serializer_class = DomainSerializer
    permission_classes = [IsAdminRoleOrReadOnly]
    lookup_field = "slug"
    pagination_class = None


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.select_related("domain").annotate(
        published_courses_count=Count("courses", filter=Q(courses__published=True), distinct=True)
    )
    serializer_class = CategorySerializer
    permission_classes = [IsAdminRoleOrReadOnly]
    lookup_field = "slug"
    pagination_class = None  # toujours renvoyée en liste complète (utilisée pour les filtres/menus)


def _enrolled_ids(user):
    if not user or not user.is_authenticated:
        return set()
    return set(CourseEnrollment.objects.filter(user=user).values_list("course_id", flat=True))


def _purchased_pdf_ids(user):
    if not user or not user.is_authenticated:
        return set()
    return set(PDFPurchase.objects.filter(user=user).values_list("pdf_product_id", flat=True))


class CourseViewSet(viewsets.ModelViewSet):
    """
    Catalogue de cours (playlists complètes).
    Filtres: ?category=<slug>&level=&language=&is_free=&search=&ordering=
    """
    queryset = Course.objects.select_related("instructor", "category").filter(published=True)
    permission_classes = [IsInstructorOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        "level", "language", "is_free", "category__slug", "category__domain__slug", "instructor__id"
    ]
    search_fields = ["title", "subtitle", "description"]
    ordering_fields = ["created_at", "price", "rating_avg", "students_count", "total_duration_minutes"]
    lookup_field = "slug"

    def get_queryset(self):
        # Une liste catalogue n'a besoin ni des leçons ni des PDF internes. Les précharger sur
        # chaque carte multipliait inutilement le volume SQL et Python et était la principale
        # source de lenteur du catalogue. On ne charge ces relations que pour le détail.
        qs = Course.objects.select_related("instructor", "category", "category__domain")
        if self.action in ("retrieve",):
            qs = qs.prefetch_related("sections__lessons", "pdf_resources")
        user = self.request.user
        if user.is_authenticated and user.role in ("instructor", "admin"):
            if self.action in ("my_courses",):
                return qs.filter(instructor=user)
            if user.role == "admin":
                return qs
            return qs.filter(Q(published=True) | Q(instructor=user))
        return qs.filter(published=True)

    def get_serializer_class(self):
        if self.action == "list":
            return CourseListSerializer
        if self.action in ("create", "update", "partial_update"):
            return CourseWriteSerializer
        return CourseDetailSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["enrolled_course_ids"] = _enrolled_ids(self.request.user)
        return ctx

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def my_courses(self, request):
        """Cours créés par l'instructeur connecté."""
        qs = self.get_queryset().filter(instructor=request.user)
        page = self.paginate_queryset(qs)
        serializer = CourseListSerializer(page if page is not None else qs, many=True, context=self.get_serializer_context())
        return self.get_paginated_response(serializer.data) if page is not None else Response(serializer.data)

    @action(detail=False, methods=["get"])
    def featured(self, request):
        qs = self.get_queryset().filter(published=True, featured=True)[:8]
        serializer = CourseListSerializer(qs, many=True, context=self.get_serializer_context())
        return Response(serializer.data)


class SectionViewSet(viewsets.ModelViewSet):
    serializer_class = SectionWriteSerializer
    permission_classes = [IsInstructorOrAdminOnly]
    filterset_fields = ["course"]

    def get_queryset(self):
        qs = Section.objects.select_related("course__instructor")
        return qs if self.request.user.role == "admin" else qs.filter(course__instructor=self.request.user)


class LessonViewSet(viewsets.ModelViewSet):
    serializer_class = LessonWriteSerializer
    permission_classes = [IsInstructorOrAdminOnly]
    filterset_fields = ["section"]

    def get_queryset(self):
        qs = Lesson.objects.select_related("section__course__instructor")
        return qs if self.request.user.role == "admin" else qs.filter(section__course__instructor=self.request.user)


    def _section_for_upload(self, section_id):
        try:
            section = Section.objects.select_related("course__instructor").get(pk=section_id)
        except (Section.DoesNotExist, TypeError, ValueError):
            return None
        if self.request.user.role != "admin" and section.course.instructor_id != self.request.user.id:
            return None
        return section

    @action(detail=False, methods=["get"], url_path="upload-capabilities")
    def upload_capabilities(self, request):
        from .direct_uploads import direct_multipart_enabled, part_size_bytes
        return Response({
            "direct_multipart": direct_multipart_enabled(),
            "part_size_bytes": part_size_bytes(),
            "max_video_upload_mb": settings.MAX_VIDEO_UPLOAD_MB,
        })

    @action(detail=False, methods=["post"], url_path="direct-upload-start")
    def direct_upload_start(self, request):
        from .direct_uploads import direct_multipart_enabled, initiate_multipart_upload

        if not direct_multipart_enabled():
            return Response({"detail": "Upload direct indisponible sur ce stockage."}, status=status.HTTP_409_CONFLICT)
        section = self._section_for_upload(request.data.get("section"))
        if not section:
            return Response({"detail": "Section introuvable ou non autorisée."}, status=status.HTTP_403_FORBIDDEN)
        try:
            size = int(request.data.get("size") or 0)
            payload = initiate_multipart_upload(
                user_id=request.user.id,
                filename=str(request.data.get("filename") or ""),
                size=size,
            )
        except Exception as exc:
            from rest_framework.exceptions import ValidationError
            if isinstance(exc, ValidationError):
                raise
            return Response({"detail": "Impossible d'initialiser l'upload direct."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({"section": section.id, **payload}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="direct-upload-part")
    def direct_upload_part(self, request):
        from .direct_uploads import presign_upload_part
        try:
            part_number = int(request.data.get("part_number") or 0)
            url = presign_upload_part(
                user_id=request.user.id,
                object_key=str(request.data.get("object_key") or ""),
                upload_id=str(request.data.get("upload_id") or ""),
                part_number=part_number,
            )
        except Exception as exc:
            from rest_framework.exceptions import ValidationError
            if isinstance(exc, ValidationError):
                raise
            return Response({"detail": "Impossible de signer ce bloc vidéo."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({"url": url, "part_number": part_number})

    @action(detail=False, methods=["post"], url_path="direct-upload-complete")
    def direct_upload_complete(self, request):
        from .direct_uploads import complete_multipart_upload

        raw_parts = request.data.get("parts", [])
        if isinstance(raw_parts, str):
            try:
                raw_parts = json.loads(raw_parts)
            except json.JSONDecodeError:
                raw_parts = []
        payload = {
            "section": request.data.get("section"),
            "title": request.data.get("title"),
            "order": request.data.get("order", 1),
            "is_preview": request.data.get("is_preview", False),
            "description": request.data.get("description", ""),
            "subtitles_file": request.FILES.get("subtitles_file"),
            "transcript": request.data.get("transcript", ""),
            "offline_download_allowed": request.data.get("offline_download_allowed", False),
            "object_key": request.data.get("object_key"),
            "upload_id": request.data.get("upload_id"),
            "expected_size": request.data.get("expected_size"),
            "parts": raw_parts,
        }
        serializer = LessonDirectCompleteSerializer(data=payload, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        result = complete_multipart_upload(
            user_id=request.user.id,
            object_key=data["object_key"],
            upload_id=data["upload_id"],
            parts=data["parts"],
            expected_size=data["expected_size"],
        )
        try:
            with transaction.atomic():
                lesson = Lesson.objects.create(
                    section=data["section"],
                    title=data["title"],
                    video_file=result["object_key"],
                    duration_minutes=0,
                    order=data.get("order", 1),
                    is_preview=data.get("is_preview", False),
                    description=data.get("description", ""),
                    subtitles_file=data.get("subtitles_file"),
                    transcript=data.get("transcript", ""),
                    offline_download_allowed=data.get("offline_download_allowed", False),
                    streaming_status="pending",
                    streaming_error="Vidéo en attente de préparation.",
                )

                def enqueue():
                    try:
                        normalize_lesson_video.delay(lesson.id)
                    except Exception:
                        Lesson.objects.filter(pk=lesson.id).update(
                            streaming_status="pending",
                            streaming_error="Worker vidéo temporairement indisponible.",
                        )

                transaction.on_commit(enqueue)
        except Exception:
            # L'objet a déjà été finalisé dans le bucket : éviter un média orphelin si la
            # création SQL échoue après coup.
            try:
                from django.core.files.storage import default_storage
                default_storage.delete(result["object_key"])
            except Exception:
                pass
            raise

        return Response({
            "id": lesson.id,
            "status": "queued",
            "streaming_status": lesson.streaming_status,
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="direct-upload-abort")
    def direct_upload_abort(self, request):
        from .direct_uploads import abort_multipart_upload
        try:
            abort_multipart_upload(
                user_id=request.user.id,
                object_key=str(request.data.get("object_key") or ""),
                upload_id=str(request.data.get("upload_id") or ""),
            )
        except Exception:
            # L'abandon est best-effort : un nettoyage de cycle de vie du bucket peut aussi
            # supprimer les multipart incomplets côté fournisseur.
            pass
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="repair-video")
    def repair_video(self, request, pk=None):
        """Lance en arrière-plan la conversion d'une vidéo existante vers H.264/AAC."""
        lesson = self.get_object()
        if not lesson.video_file:
            return Response({"detail": "Cette leçon n'a pas de fichier vidéo uploadé à réparer."}, status=status.HTTP_400_BAD_REQUEST)
        task = normalize_lesson_video.delay(lesson.id)
        return Response({"task_id": task.id, "status": "queued"}, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["get"], url_path=r"repair-video-status/(?P<task_id>[^/.]+)")
    def repair_video_status(self, request, pk=None, task_id=None):
        """Retourne l'état d'une conversion lancée pour cette leçon."""
        lesson = self.get_object()
        task = AsyncResult(task_id)
        state = task.state
        if state == "SUCCESS":
            result = task.result if isinstance(task.result, dict) else {"detail": str(task.result)}
            if result.get("lesson_id") != lesson.id:
                return Response({"detail": "Tâche de réparation invalide pour cette leçon."}, status=status.HTTP_403_FORBIDDEN)
            return Response({"state": state, **result})
        if state == "FAILURE":
            return Response({"state": state, "detail": "La conversion vidéo a échoué. Vérifiez les logs du worker Celery."})
        return Response({"state": state})


    @action(detail=True, methods=["post"], url_path="prepare-streaming")
    def prepare_streaming(self, request, pk=None):
        """(Re)génère le HLS adaptatif + audio faible débit d'une leçon uploadée."""
        lesson = self.get_object()
        if not lesson.video_file:
            return Response({"detail": "Le streaming adaptatif nécessite un fichier vidéo uploadé."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            Lesson.objects.filter(pk=lesson.id).update(streaming_status="pending", streaming_error="Vidéo en attente de préparation.")
            task = normalize_lesson_video.delay(lesson.id)
        except Exception:
            return Response({"detail": "Le worker de transcodage est temporairement indisponible."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({"task_id": task.id, "status": "queued"}, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["get"], url_path="streaming-status")
    def streaming_status(self, request, pk=None):
        lesson = self.get_object()
        payload = {
            "lesson_id": lesson.id,
            "status": lesson.streaming_status,
            "variants": lesson.streaming_variants,
            "detail": lesson.streaming_error if lesson.streaming_status == "failed" else "",
            "hls_url": None,
            "audio_hls_url": None,
            "data_saver_hls_url": None,
        }
        if lesson.streaming_status == "ready" and lesson.hls_master_path:
            payload["hls_url"] = sign_hls_path(lesson.hls_master_path)
            payload["data_saver_hls_url"] = sign_hls_path(lesson.hls_master_path, max_height=settings.HLS_DATA_SAVER_MAX_HEIGHT)
            if lesson.audio_hls_path:
                payload["audio_hls_url"] = sign_hls_path(lesson.audio_hls_path)
        return Response(payload)


class PDFResourceViewSet(viewsets.ModelViewSet):
    serializer_class = PDFResourceWriteSerializer
    permission_classes = [IsInstructorOrAdminOnly]
    filterset_fields = ["course"]

    def get_queryset(self):
        qs = PDFResource.objects.select_related("course__instructor")
        return qs if self.request.user.role == "admin" else qs.filter(course__instructor=self.request.user)


class PDFProductViewSet(viewsets.ModelViewSet):
    """Catalogue de PDF vendus SEULS (indépendamment des cours vidéo)."""
    permission_classes = [IsInstructorOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        "level", "language", "is_free", "category__slug", "category__domain__slug", "instructor__id"
    ]
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "price", "rating_avg", "downloads_count"]
    lookup_field = "slug"

    def get_queryset(self):
        qs = PDFProduct.objects.select_related("instructor", "category", "category__domain")
        user = self.request.user
        if user.is_authenticated and user.role == "admin":
            return qs
        if user.is_authenticated and user.role == "instructor":
            if self.action == "my_pdfs":
                return qs.filter(instructor=user)
            return qs.filter(Q(published=True) | Q(instructor=user))
        return qs.filter(published=True)

    def get_serializer_class(self):
        if self.action == "list":
            return PDFProductListSerializer
        if self.action in ("create", "update", "partial_update"):
            return PDFProductWriteSerializer
        return PDFProductDetailSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["purchased_pdf_ids"] = _purchased_pdf_ids(self.request.user)
        return ctx

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def my_pdfs(self, request):
        qs = self.get_queryset().filter(instructor=request.user)
        page = self.paginate_queryset(qs)
        serializer = PDFProductDetailSerializer(page if page is not None else qs, many=True, context=self.get_serializer_context())
        return self.get_paginated_response(serializer.data) if page is not None else Response(serializer.data)
