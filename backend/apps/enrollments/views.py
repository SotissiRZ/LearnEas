from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.conf import settings
from django.core import signing
from django.utils import timezone
from django.db import models, transaction
import math
from datetime import datetime
from rest_framework import viewsets, permissions, status, filters, generics
from rest_framework.views import APIView
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.catalog.models import Lesson, Course, PDFProduct
from .models import CourseEnrollment, LessonProgress, LessonNote, PDFPurchase, Wishlist, Certificate, CertificateEvent
from .serializers import (
    CourseEnrollmentSerializer, LessonProgressSerializer, LessonNoteSerializer, PDFPurchaseSerializer, WishlistSerializer,
    CertificateSerializer, PublicCertificateSerializer,
)


def _nonnegative_int(value, default=0):
    try:
        return max(0, int(float(value if value is not None else default)))
    except (TypeError, ValueError):
        return None


def _playback_payload(request, progress, lesson):
    """Normalise position de reprise et temps réellement regardé.

    v81 sépare enfin la position (`position_seconds`) du temps de visionnage cumulé
    (`watched_delta_seconds`). L'ancien `watched_seconds` reste accepté pour les clients
    v80 et les tests historiques.
    """
    has_v81_fields = "position_seconds" in request.data or "watched_delta_seconds" in request.data
    now = timezone.now()
    managed_video = bool(lesson.video_file)
    if not has_v81_fields:
        legacy = _nonnegative_int(request.data.get("watched_seconds"), progress.last_position_seconds)
        if legacy is None:
            return None
        # Compatibilité de position uniquement pour les anciens clients. Sur une vidéo hébergée,
        # `watched_seconds=position` permettrait sinon de tricher en sautant directement à la fin.
        watched_total = progress.watched_seconds if managed_video else max(progress.watched_seconds, legacy)
        return {"position": legacy, "watched_total": watched_total, "heartbeat": progress.last_watch_heartbeat_at, "credited_delta": 0}

    position = _nonnegative_int(request.data.get("position_seconds"), progress.last_position_seconds)
    requested_delta = _nonnegative_int(request.data.get("watched_delta_seconds"), 0)
    if position is None or requested_delta is None:
        return None

    offline_delta = _nonnegative_int(request.data.get("offline_watched_seconds"), 0) or 0
    offline_token = str(request.data.get("offline_progress_token") or "")
    delta = 0
    if managed_video and offline_delta > 0 and offline_token:
        try:
            payload = signing.loads(
                offline_token, salt="kalanpro.offline-progress",
                max_age=getattr(settings, "OFFLINE_PROGRESS_TOKEN_MAX_AGE", 30 * 24 * 3600),
            )
            if int(payload.get("lesson_id") or 0) != lesson.id or int(payload.get("user_id") or 0) != request.user.id:
                raise signing.BadSignature("offline token mismatch")
            issued_at = datetime.fromtimestamp(int(payload.get("issued_at") or 0), tz=timezone.get_current_timezone())
            anchor = progress.last_watch_heartbeat_at or issued_at
            elapsed = max(0.0, (now - anchor).total_seconds())
            max_credit = max(0, int(elapsed * 2.2))
            duration_cap = int(lesson.duration_seconds or lesson.duration_minutes * 60 or 0)
            if duration_cap > 0:
                max_credit = min(max_credit, duration_cap)
            delta = min(offline_delta, max_credit)
        except Exception:
            delta = 0
    else:
        requested_delta = min(requested_delta, 120)
        delta = requested_delta
    if managed_video and requested_delta > 0 and not (offline_delta > 0 and offline_token):
        # Défense côté serveur contre les appels API répétés : on ne crédite pas plus de contenu
        # qu'il n'est physiquement possible d'en regarder depuis le dernier heartbeat. Le lecteur
        # autorise jusqu'à 2x, d'où une marge de 2.2x. Le premier heartbeat crédite au plus 20 s.
        if progress.last_watch_heartbeat_at:
            elapsed = max(0.0, (now - progress.last_watch_heartbeat_at).total_seconds())
            max_credit = min(120, max(0, int(elapsed * 2.2)))
        else:
            max_credit = 20
        delta = min(requested_delta, max_credit)

    duration_limit = int(lesson.duration_seconds or 0)
    if duration_limit <= 0 and lesson.duration_minutes:
        duration_limit = int(lesson.duration_minutes) * 60 + 60
    if duration_limit > 0:
        position = min(position, duration_limit)
    return {"position": position, "watched_total": progress.watched_seconds + delta, "heartbeat": now if delta > 0 else progress.last_watch_heartbeat_at, "credited_delta": delta}


def _managed_video_completion_requirement(lesson):
    """Retourne (required_seconds, threshold) pour une vidéo hébergée par KalanPro.

    Les URL externes ne sont pas vérifiables de façon fiable par le navigateur et conservent
    donc la validation manuelle historique.
    """
    if not lesson.video_file:
        return 0, 0
    duration_seconds = int(lesson.duration_seconds or 0)
    if duration_seconds <= 0 and lesson.duration_minutes:
        duration_seconds = int(lesson.duration_minutes) * 60
    if duration_seconds <= 0:
        return 0, 0
    threshold = max(50, min(100, int(getattr(lesson.section.course, "video_completion_threshold_percent", 90) or 90)))
    return max(1, math.ceil(duration_seconds * threshold / 100)), threshold


class CourseEnrollmentViewSet(viewsets.ReadOnlyModelViewSet):
    """Liste 'Mes cours' de l'utilisateur connecté + suivi de progression."""
    serializer_class = CourseEnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CourseEnrollment.objects.filter(user=self.request.user).select_related("course").prefetch_related("lesson_progress")

    @action(detail=True, methods=["post"])
    def mark_lesson_complete(self, request, pk=None):
        enrollment = self.get_object()
        lesson_id = request.data.get("lesson_id")
        lesson = get_object_or_404(Lesson, id=lesson_id, section__course=enrollment.course)

        with transaction.atomic():
            progress, _ = LessonProgress.objects.get_or_create(enrollment=enrollment, lesson=lesson)
            progress = LessonProgress.objects.select_for_update().get(pk=progress.pk)
            playback = _playback_payload(request, progress, lesson)
            if playback is None:
                return Response({"position_seconds": ["Valeur invalide."]}, status=400)
            progress.watched_seconds = playback["watched_total"]
            progress.last_position_seconds = playback["position"]
            progress.last_watch_heartbeat_at = playback["heartbeat"]
            required_seconds, threshold = _managed_video_completion_requirement(lesson)
            if lesson.video_file and required_seconds <= 0:
                progress.save(update_fields=["watched_seconds", "last_position_seconds", "last_watch_heartbeat_at", "updated_at"])
                return Response({
                    "detail": "Cette vidéo est encore en préparation. Sa durée doit être connue avant validation.",
                    "watched_percent": 0,
                    "required_percent": threshold or max(50, min(100, int(getattr(enrollment.course, "video_completion_threshold_percent", 90) or 90))),
                    "watched_seconds": progress.watched_seconds,
                    "required_seconds": None,
                }, status=status.HTTP_409_CONFLICT)
            if required_seconds and progress.watched_seconds < required_seconds:
                progress.save(update_fields=["watched_seconds", "last_position_seconds", "last_watch_heartbeat_at", "updated_at"])
                watched_percent = min(100, int((progress.watched_seconds / max(1, lesson.duration_seconds or lesson.duration_minutes * 60)) * 100))
                return Response({
                    "detail": f"Regardez au moins {threshold} % de cette vidéo pour la terminer.",
                    "watched_percent": watched_percent,
                    "required_percent": threshold,
                    "watched_seconds": progress.watched_seconds,
                    "required_seconds": required_seconds,
                }, status=status.HTTP_409_CONFLICT)
            progress.completed = True
            progress.save()

        total = Lesson.objects.filter(section__course=enrollment.course).count()
        done = LessonProgress.objects.filter(enrollment=enrollment, completed=True).count()
        enrollment.progress_percent = int((done / total) * 100) if total else 0
        enrollment.last_accessed_lesson = lesson
        from apps.projects.services import required_projects_status
        projects_complete = required_projects_status(enrollment)["complete"]
        if enrollment.progress_percent >= 100 and projects_complete and not enrollment.completed:
            enrollment.completed = True
            enrollment.completed_at = timezone.now()
        enrollment.save()

        # Le certificat peut être configuré à un seuil différent de 100 %.
        if enrollment.course.certificate_enabled and enrollment.course.certificate_auto_issue:
            from .certificates import issue_course_certificate, course_eligibility
            eligibility = course_eligibility(enrollment)
            if eligibility["eligible"]:
                issue_course_certificate(enrollment, issued_by=enrollment.course.instructor)
                enrollment.refresh_from_db()

        return Response(CourseEnrollmentSerializer(enrollment).data)

    @action(detail=True, methods=["post"], url_path="update-lesson-progress")
    def update_lesson_progress(self, request, pk=None):
        """Mémorise la position de lecture sans marquer artificiellement la leçon comme terminée."""
        enrollment = self.get_object()
        lesson_id = request.data.get("lesson_id")
        lesson = get_object_or_404(Lesson, id=lesson_id, section__course=enrollment.course)
        with transaction.atomic():
            progress, _ = LessonProgress.objects.get_or_create(enrollment=enrollment, lesson=lesson)
            # Deux syncs peuvent se croiser (timer + pause/navigation). Le verrou évite de
            # perdre un `watched_delta_seconds` lors d'une mise à jour concurrente.
            progress = LessonProgress.objects.select_for_update().get(pk=progress.pk)
            playback = _playback_payload(request, progress, lesson)
            if playback is None:
                return Response({"position_seconds": ["Valeur invalide."]}, status=400)
            progress.watched_seconds = playback["watched_total"]
            # La position de reprise peut volontairement reculer si l'apprenant revient en arrière.
            # Le temps réellement regardé, lui, reste cumulatif.
            progress.last_position_seconds = playback["position"]
            progress.last_watch_heartbeat_at = playback["heartbeat"]
            progress.save(update_fields=["watched_seconds", "last_position_seconds", "last_watch_heartbeat_at", "updated_at"])
            enrollment.last_accessed_lesson = lesson
            enrollment.save(update_fields=["last_accessed_lesson"])
        data = LessonProgressSerializer(progress).data
        # Le client conserve la partie hors-ligne non encore créditée si le plafond anti-triche
        # (temps mural / token signé) n'a accepté qu'une fraction de ce qu'il avait accumulé.
        data["credited_watched_seconds"] = int(playback.get("credited_delta") or 0)
        return Response(data)

    @action(detail=True, methods=["get"])
    def certificate(self, request, pk=None):
        enrollment = self.get_object()
        from .certificates import issue_course_certificate, course_eligibility
        certificate = Certificate.objects.filter(course_enrollment=enrollment).first()
        if not certificate:
            eligibility = course_eligibility(enrollment)
            if not eligibility["eligible"]:
                return Response({"detail": eligibility["reason"] or "Certificat non disponible."}, status=400)
            certificate, _ = issue_course_certificate(enrollment, issued_by=enrollment.course.instructor)
        return Response(CertificateSerializer(certificate, context={"request": request}).data)



class LessonNoteViewSet(viewsets.ModelViewSet):
    """Carnet personnel : chaque utilisateur ne peut lire et modifier que ses propres notes."""
    serializer_class = LessonNoteSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["lesson"]
    ordering_fields = ["timestamp_seconds", "created_at", "updated_at"]
    ordering = ["timestamp_seconds", "created_at"]

    def get_queryset(self):
        qs = LessonNote.objects.filter(user=self.request.user).select_related(
            "lesson", "lesson__section", "lesson__section__course"
        )
        course_id = self.request.query_params.get("course")
        if course_id:
            qs = qs.filter(lesson__section__course_id=course_id)
        return qs

    def perform_create(self, serializer):
        lesson = serializer.validated_data["lesson"]
        course = lesson.section.course
        user = self.request.user
        has_access = (
            user.role == "admin"
            or course.instructor_id == user.id
            or course.is_free
            or CourseEnrollment.objects.filter(user=user, course=course).exists()
        )
        if not has_access:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Vous devez avoir accès à ce cours pour prendre une note.")
        serializer.save(user=user)


class WishlistViewSet(viewsets.ModelViewSet):
    serializer_class = WishlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        course_id = request.data.get("course")
        pdf_id = request.data.get("pdf_product")
        if bool(course_id) == bool(pdf_id):
            return Response({"detail": "Choisissez exactement un cours ou un PDF."}, status=400)
        if course_id:
            from apps.catalog.models import Course
            target = Course.objects.filter(id=course_id, published=True).first()
            if not target:
                return Response({"course": ["Cours introuvable ou non publié."]}, status=404)
            obj, created = Wishlist.objects.get_or_create(user=request.user, course=target, pdf_product=None)
        else:
            from apps.catalog.models import PDFProduct
            target = PDFProduct.objects.filter(id=pdf_id, published=True).first()
            if not target:
                return Response({"pdf_product": ["PDF introuvable ou non publié."]}, status=404)
            obj, created = Wishlist.objects.get_or_create(user=request.user, course=None, pdf_product=target)
        return Response(WishlistSerializer(obj).data, status=status.HTTP_201_CREATED if created else 200)


class MyPDFsViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PDFPurchaseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PDFPurchase.objects.filter(user=self.request.user).select_related("pdf_product")


class CertificateViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CertificateSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["certificate_number", "student_name", "content_title", "instructor_name"]
    ordering_fields = ["issued_at", "expires_at", "achievement_percent"]
    ordering = ["-issued_at"]

    def get_queryset(self):
        user = self.request.user
        qs = Certificate.objects.select_related(
            "user", "issued_by", "supersedes", "course_enrollment__course__instructor",
            "formation_enrollment__formation__instructor",
        ).prefetch_related("events__actor", "replacement_certificates")
        if user.role == "admin":
            return qs
        if user.role == "instructor":
            return qs.filter(
                models.Q(course_enrollment__course__instructor=user)
                | models.Q(formation_enrollment__formation__instructor=user)
                | models.Q(formation_enrollment__formation__co_instructor=user)
            ).distinct()
        return qs.filter(user=user)

    @action(detail=False, methods=["get"], url_path="eligible")
    def eligible(self, request):
        if request.user.role not in ("instructor", "admin"):
            return Response({"detail": "Compte instructeur requis."}, status=403)
        from apps.formations.models import FormationEnrollment
        from .certificates import course_eligibility, formation_eligibility
        rows = []
        course_id = request.query_params.get("course")
        formation_id = request.query_params.get("formation")
        if course_id:
            qs = CourseEnrollment.objects.filter(course_id=course_id).select_related("user", "course__instructor")
            if request.user.role != "admin":
                qs = qs.filter(course__instructor=request.user)
            for e in qs:
                info = course_eligibility(e)
                latest_certificate = e.certificate_records.order_by("-issued_at", "-id").first()
                rows.append({"enrollment_id": e.id, "kind": "course", "user_id": e.user_id,
                             "student_name": e.user.get_full_name() or e.user.username,
                             "student_email": e.user.email, **info,
                             "certificate_id": latest_certificate.id if latest_certificate else None,
                             "certificate_status": latest_certificate.effective_status if latest_certificate else None})
        elif formation_id:
            qs = FormationEnrollment.objects.filter(formation_id=formation_id).select_related("user", "formation__instructor", "formation__co_instructor")
            if request.user.role != "admin":
                qs = qs.filter(models.Q(formation__instructor=request.user) | models.Q(formation__co_instructor=request.user))
            for e in qs:
                info = formation_eligibility(e)
                latest_certificate = e.certificate_records.order_by("-issued_at", "-id").first()
                rows.append({"enrollment_id": e.id, "kind": "formation", "user_id": e.user_id,
                             "student_name": e.user.get_full_name() or e.user.username,
                             "student_email": e.user.email, **info,
                             "certificate_id": latest_certificate.id if latest_certificate else None,
                             "certificate_status": latest_certificate.effective_status if latest_certificate else None})
        else:
            return Response({"detail": "Indiquez course ou formation."}, status=400)
        return Response(rows)

    @action(detail=False, methods=["post"], url_path="issue")
    def issue(self, request):
        if request.user.role not in ("instructor", "admin"):
            return Response({"detail": "Compte instructeur requis."}, status=403)
        from apps.formations.models import FormationEnrollment
        from .certificates import issue_course_certificate, issue_formation_certificate
        force = bool(request.data.get("force", False)) and request.user.role == "admin"
        try:
            if request.data.get("course_enrollment_id"):
                e = CourseEnrollment.objects.select_related("course__instructor", "user").get(id=request.data["course_enrollment_id"])
                if request.user.role != "admin" and e.course.instructor_id != request.user.id:
                    return Response({"detail": "Accès refusé."}, status=403)
                cert, _ = issue_course_certificate(e, issued_by=request.user, force=force)
            elif request.data.get("formation_enrollment_id"):
                e = FormationEnrollment.objects.select_related("formation__instructor", "formation__co_instructor", "user").get(id=request.data["formation_enrollment_id"])
                if request.user.role != "admin" and request.user.id not in (e.formation.instructor_id, e.formation.co_instructor_id):
                    return Response({"detail": "Accès refusé."}, status=403)
                cert, _ = issue_formation_certificate(e, issued_by=request.user, force=force)
            else:
                return Response({"detail": "Inscription requise."}, status=400)
        except (CourseEnrollment.DoesNotExist, FormationEnrollment.DoesNotExist):
            return Response({"detail": "Inscription introuvable."}, status=404)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(self.get_serializer(cert).data, status=201)

    @action(detail=False, methods=["post"], url_path="issue-bulk")
    def issue_bulk(self, request):
        """Délivre en lot les certificats éligibles d'un contenu appartenant à l'instructeur.

        L'admin peut passer force=true pour ignorer le seuil, mais un certificat déjà actif
        n'est jamais dupliqué. Les certificats révoqués ne sont pas réémis silencieusement en lot.
        """
        if request.user.role not in ("instructor", "admin"):
            return Response({"detail": "Compte instructeur requis."}, status=403)
        from apps.formations.models import FormationEnrollment
        from .certificates import (
            course_eligibility, formation_eligibility,
            issue_course_certificate, issue_formation_certificate,
        )
        force = bool(request.data.get("force", False)) and request.user.role == "admin"
        course_id = request.data.get("course_id")
        formation_id = request.data.get("formation_id")
        if bool(course_id) == bool(formation_id):
            return Response({"detail": "Indiquez exactement course_id ou formation_id."}, status=400)

        if course_id:
            enrollments = CourseEnrollment.objects.filter(course_id=course_id).select_related("user", "course__instructor")
            if request.user.role != "admin":
                enrollments = enrollments.filter(course__instructor=request.user)
            eligibility_fn, issue_fn, relation = course_eligibility, issue_course_certificate, "course"
        else:
            enrollments = FormationEnrollment.objects.filter(formation_id=formation_id).select_related(
                "user", "formation__instructor", "formation__co_instructor"
            )
            if request.user.role != "admin":
                enrollments = enrollments.filter(
                    models.Q(formation__instructor=request.user) | models.Q(formation__co_instructor=request.user)
                ).distinct()
            eligibility_fn, issue_fn, relation = formation_eligibility, issue_formation_certificate, "formation"

        issued, skipped, errors = [], [], []
        for enrollment in enrollments:
            existing = Certificate.objects.filter(
                **{f"{relation}_enrollment": enrollment}
            ).first()
            if existing:
                skipped.append({"enrollment_id": enrollment.id, "reason": f"Certificat déjà {existing.effective_status}."})
                continue
            info = eligibility_fn(enrollment)
            if not force and not info["eligible"]:
                skipped.append({"enrollment_id": enrollment.id, "reason": info["reason"] or "Non éligible."})
                continue
            try:
                certificate, _ = issue_fn(enrollment, issued_by=request.user, force=force)
                issued.append(CertificateSerializer(certificate, context={"request": request}).data)
            except ValueError as exc:
                errors.append({"enrollment_id": enrollment.id, "detail": str(exc)})
        return Response({"issued": issued, "skipped": skipped, "errors": errors, "issued_count": len(issued)})

    @action(detail=True, methods=["post"], url_path="revoke")
    def revoke(self, request, pk=None):
        certificate = self.get_object()
        if request.user.role not in ("instructor", "admin"):
            return Response({"detail": "Accès refusé."}, status=403)
        if certificate.effective_status != Certificate.Status.ACTIVE:
            return Response({"detail": "Seul un certificat actuellement valide peut être révoqué."}, status=400)
        reason = str(request.data.get("reason", "")).strip()
        if len(reason) < 3:
            return Response({"reason": ["Indiquez un motif de révocation (3 caractères minimum)."]}, status=400)
        certificate.status = Certificate.Status.REVOKED
        certificate.revoked_at = timezone.now()
        certificate.revocation_reason = reason[:2000]
        certificate.save(update_fields=["status", "revoked_at", "revocation_reason"])
        CertificateEvent.objects.create(
            certificate=certificate, event_type=CertificateEvent.EventType.REVOKED, actor=request.user,
            details={"reason": certificate.revocation_reason},
        )
        return Response(self.get_serializer(certificate).data)

    @action(detail=True, methods=["post"], url_path="reissue")
    def reissue(self, request, pk=None):
        certificate = self.get_object()
        if request.user.role not in ("instructor", "admin"):
            return Response({"detail": "Accès refusé."}, status=403)
        if certificate.effective_status == Certificate.Status.ACTIVE:
            return Response({"detail": "Révoquez d'abord le certificat actif avant de le réémettre."}, status=400)
        latest_replacement = certificate.replacement_certificates.order_by("-issued_at", "-id").first()
        if latest_replacement:
            return Response(
                {
                    "detail": "Ce certificat a déjà été remplacé. Réémettez la version la plus récente si nécessaire.",
                    "certificate_id": latest_replacement.id,
                },
                status=409,
            )
        from .certificates import issue_course_certificate, issue_formation_certificate
        if certificate.course_enrollment_id:
            replacement, _ = issue_course_certificate(
                certificate.course_enrollment, issued_by=request.user, force=True, force_new=True, supersedes=certificate
            )
        else:
            replacement, _ = issue_formation_certificate(
                certificate.formation_enrollment, issued_by=request.user, force=True, force_new=True, supersedes=certificate
            )
        return Response(self.get_serializer(replacement).data, status=201)


class CertificateVerifyView(generics.RetrieveAPIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "certificate_verify"
    serializer_class = PublicCertificateSerializer
    lookup_field = "verification_code"
    lookup_url_kwarg = "code"

    def get_queryset(self):
        from apps.accounts.models import PlatformSettings
        if not PlatformSettings.load().certificate_verification_enabled:
            return Certificate.objects.none()
        return Certificate.objects.select_related("supersedes").prefetch_related("replacement_certificates")


class CertificateLookupView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "certificate_verify"

    def get(self, request):
        from apps.accounts.models import PlatformSettings
        if not PlatformSettings.load().certificate_verification_enabled:
            return Response({"detail": "La vérification publique est désactivée."}, status=404)
        query = str(request.query_params.get("q", "")).strip()
        if not query:
            return Response({"q": ["Indiquez un numéro ou un code de vérification."]}, status=400)
        certificate = Certificate.objects.filter(certificate_number__iexact=query).first()
        if certificate is None:
            try:
                import uuid
                code = uuid.UUID(query)
            except (ValueError, TypeError, AttributeError):
                code = None
            if code:
                certificate = Certificate.objects.filter(verification_code=code).first()
        if certificate is None:
            return Response({"detail": "Certificat introuvable."}, status=404)
        return Response(PublicCertificateSerializer(certificate, context={"request": request}).data)


class CertificateQRView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "certificate_verify"

    def get(self, request, code):
        from apps.accounts.models import PlatformSettings
        from django.conf import settings
        if not PlatformSettings.load().certificate_verification_enabled:
            return Response({"detail": "La vérification publique est désactivée."}, status=404)
        certificate = get_object_or_404(Certificate, verification_code=code)
        verification_url = f"{settings.FRONTEND_URL.rstrip('/')}/certificates/verify/{certificate.verification_code}"
        try:
            import io
            import qrcode
            from qrcode.constants import ERROR_CORRECT_M
            qr = qrcode.QRCode(version=None, error_correction=ERROR_CORRECT_M, box_size=8, border=4)
            qr.add_data(verification_url)
            qr.make(fit=True)
            image = qr.make_image(fill_color="black", back_color="white")
            buf = io.BytesIO()
            image.save(buf, format="PNG")
        except Exception:
            return Response({"detail": "QR code indisponible."}, status=503)
        response = HttpResponse(buf.getvalue(), content_type="image/png")
        response["Cache-Control"] = "public, max-age=86400"
        response["Content-Disposition"] = f'inline; filename="{certificate.certificate_number}-qr.png"'
        return response


class CertificatePDFView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "certificate_verify"

    def get(self, request, code):
        from apps.accounts.models import PlatformSettings
        if not PlatformSettings.load().certificate_verification_enabled:
            return Response({"detail": "La vérification publique est désactivée."}, status=404)
        certificate = get_object_or_404(Certificate, verification_code=code)
        try:
            import io
            import qrcode
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.colors import HexColor, Color
            from reportlab.lib.utils import ImageReader
        except Exception:
            return Response({"detail": "Export PDF indisponible."}, status=503)

        buffer = io.BytesIO()
        page = landscape(A4)
        width, height = page
        pdf = canvas.Canvas(buffer, pagesize=page, pageCompression=1)
        try:
            accent = HexColor(certificate.accent_color or "#ff641a")
        except Exception:
            accent = HexColor("#ff641a")

        # Cadre et en-tête
        pdf.setStrokeColor(accent)
        pdf.setLineWidth(5)
        pdf.rect(24, 24, width - 48, height - 48)
        pdf.setLineWidth(1)
        pdf.rect(34, 34, width - 68, height - 68)
        pdf.setFillColor(accent)
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawCentredString(width / 2, height - 78, (certificate.title or "Certificat de réussite")[:90])
        pdf.setFillColorRGB(0.25, 0.25, 0.25)
        pdf.setFont("Helvetica", 10)
        if certificate.subtitle:
            pdf.drawCentredString(width / 2, height - 96, certificate.subtitle[:120])

        pdf.setFillColorRGB(0.08, 0.08, 0.08)
        pdf.setFont("Helvetica-Bold", 27)
        pdf.drawCentredString(width / 2, height - 150, certificate.student_name[:100])
        pdf.setFont("Helvetica", 12)
        pdf.setFillColorRGB(0.35, 0.35, 0.35)
        pdf.drawCentredString(width / 2, height - 176, "a satisfait aux critères de validation de")
        pdf.setFillColor(accent)
        pdf.setFont("Helvetica-Bold", 19)
        pdf.drawCentredString(width / 2, height - 204, certificate.content_title[:100])

        y = height - 242
        pdf.setFillColorRGB(0.2, 0.2, 0.2)
        pdf.setFont("Helvetica", 10)
        details = [
            f"Émetteur : {certificate.issuer_name or 'KalanPro'}",
            f"Instructeur : {certificate.instructor_name or '-'}",
            f"Résultat : {certificate.achievement_percent}%",
            f"N° : {certificate.certificate_number}",
        ]
        if certificate.completed_at:
            details.append(f"Validé le : {certificate.completed_at.strftime('%d/%m/%Y')}")
        if certificate.expires_at:
            details.append(f"Expiration : {certificate.expires_at.strftime('%d/%m/%Y')}")
        x0 = 86
        col_width = (width - 172) / 2
        for index, line in enumerate(details):
            col = index % 2
            row = index // 2
            pdf.drawString(x0 + col * col_width, y - row * 22, line[:115])

        skills = [str(v).strip() for v in (certificate.skills_snapshot or []) if str(v).strip()][:12]
        if skills:
            pdf.setFont("Helvetica-Bold", 9)
            pdf.setFillColorRGB(0.35, 0.35, 0.35)
            pdf.drawString(86, y - 82, "Compétences attestées")
            pdf.setFont("Helvetica", 9)
            pdf.drawString(86, y - 98, " • ".join(skills)[:170])

        verification_url = f"{settings.FRONTEND_URL.rstrip('/')}/certificates/verify/{certificate.verification_code}"
        qr = qrcode.QRCode(version=None, box_size=4, border=2)
        qr.add_data(verification_url)
        qr.make(fit=True)
        qr_image = qr.make_image(fill_color="black", back_color="white")
        qr_buffer = io.BytesIO()
        qr_image.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)
        qr_size = 88
        pdf.drawImage(ImageReader(qr_buffer), width - 145, 70, qr_size, qr_size, preserveAspectRatio=True, mask="auto")
        pdf.setFont("Helvetica", 7.5)
        pdf.setFillColorRGB(0.4, 0.4, 0.4)
        pdf.drawString(70, 103, f"Code de vérification : {certificate.verification_code}")
        if certificate.credential_digest:
            pdf.drawString(70, 87, f"Empreinte SHA-256 : {certificate.credential_digest[:64]}")
        pdf.drawString(70, 71, "Vérification publique : " + verification_url[:120])

        effective = certificate.effective_status
        if effective != Certificate.Status.ACTIVE:
            label = "RÉVOQUÉ" if effective == Certificate.Status.REVOKED else "EXPIRÉ"
            pdf.saveState()
            pdf.setFillColor(Color(0.75, 0.1, 0.1, alpha=0.16))
            pdf.setFont("Helvetica-Bold", 58)
            pdf.translate(width / 2, height / 2)
            pdf.rotate(24)
            pdf.drawCentredString(0, 0, label)
            pdf.restoreState()

        pdf.showPage()
        pdf.save()
        response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{certificate.certificate_number}.pdf"'
        response["Cache-Control"] = "private, max-age=300" if certificate.effective_status != Certificate.Status.ACTIVE else "public, max-age=3600"
        return response
