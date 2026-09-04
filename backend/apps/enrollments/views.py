from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.utils import timezone
from django.db import models
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

        progress, _ = LessonProgress.objects.get_or_create(enrollment=enrollment, lesson=lesson)
        progress.completed = True
        try:
            watched_seconds = max(0, int(float(request.data.get("watched_seconds", progress.watched_seconds) or 0)))
        except (TypeError, ValueError):
            watched_seconds = progress.watched_seconds
        progress.watched_seconds = max(progress.watched_seconds, watched_seconds)
        progress.last_position_seconds = watched_seconds
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
        try:
            watched_seconds = max(0, int(float(request.data.get("watched_seconds", 0) or 0)))
        except (TypeError, ValueError):
            return Response({"watched_seconds": ["Valeur invalide."]}, status=400)

        progress, _ = LessonProgress.objects.get_or_create(enrollment=enrollment, lesson=lesson)
        # Ne jamais faire reculer la progression mémorisée suite à une requête arrivée en retard.
        progress.watched_seconds = max(progress.watched_seconds, watched_seconds)
        progress.last_position_seconds = watched_seconds
        progress.save(update_fields=["watched_seconds", "last_position_seconds", "updated_at"])
        enrollment.last_accessed_lesson = lesson
        enrollment.save(update_fields=["last_accessed_lesson"])
        return Response(LessonProgressSerializer(progress).data)

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
