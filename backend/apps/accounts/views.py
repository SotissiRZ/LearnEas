from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.password_validation import validate_password
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from django.db.models import Avg, Count, Q
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils import timezone
from rest_framework import generics, permissions, status, viewsets, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer

from .serializers import (
    RegisterSerializer, UserSerializer, AdminUserSerializer, AdminUserCreateSerializer,
    PlatformSettingsSerializer, InstructorApplicationSerializer, InstructorApplicationAdminSerializer,
)
from .models import PlatformSettings, InstructorApplication
from apps.common.throttles import AuthRateThrottle, PasswordResetRateThrottle, RefreshRateThrottle
from .authentication import password_fingerprint

User = get_user_model()


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["full_name"] = user.get_full_name() or user.username
        token["pwd"] = password_fingerprint(user)
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


def _set_refresh_cookie(response, refresh_value: str):
    response.set_cookie(
        settings.AUTH_REFRESH_COOKIE_NAME,
        refresh_value,
        max_age=settings.AUTH_REFRESH_COOKIE_MAX_AGE,
        httponly=True,
        secure=settings.AUTH_REFRESH_COOKIE_SECURE,
        samesite=settings.AUTH_REFRESH_COOKIE_SAMESITE,
        path=settings.AUTH_REFRESH_COOKIE_PATH,
        domain=settings.AUTH_REFRESH_COOKIE_DOMAIN,
    )


def _clear_refresh_cookie(response):
    response.delete_cookie(
        settings.AUTH_REFRESH_COOKIE_NAME,
        path=settings.AUTH_REFRESH_COOKIE_PATH,
        domain=settings.AUTH_REFRESH_COOKIE_DOMAIN,
        samesite=settings.AUTH_REFRESH_COOKIE_SAMESITE,
    )


def _cookie_request_origin_allowed(request) -> bool:
    """Refuse l'usage d'un cookie d'auth depuis une origine navigateur inconnue.

    DRF est volontairement JWT-only et n'utilise donc pas SessionAuthentication/CSRF pour
    l'API. Les endpoints qui *consomment* le refresh HttpOnly ajoutent ce contrôle Origin
    explicite. Les clients non-navigateurs sans en-tête Origin restent autorisés.
    """
    origin = (request.headers.get("Origin") or "").rstrip("/")
    if not origin:
        return True
    allowed = {str(value).rstrip("/") for value in settings.CORS_ALLOWED_ORIGINS}
    allowed.update({
        str(getattr(settings, "FRONTEND_URL", "")).rstrip("/"),
        str(getattr(settings, "BACKEND_PUBLIC_URL", "")).rstrip("/"),
    })
    try:
        own_origin = f"{'https' if request.is_secure() else 'http'}://{request.get_host()}".rstrip("/")
        allowed.add(own_origin)
    except Exception:
        pass
    allowed.discard("")
    return origin in allowed


class LoginView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer
    throttle_classes = [AuthRateThrottle]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        refresh_value = response.data.pop("refresh", None) if isinstance(response.data, dict) else None
        if refresh_value:
            _set_refresh_cookie(response, refresh_value)
        return response


class CookieTokenRefreshView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [RefreshRateThrottle]

    def post(self, request):
        if not _cookie_request_origin_allowed(request):
            return Response({"detail": "Origine non autorisée."}, status=status.HTTP_403_FORBIDDEN)
        refresh_value = request.COOKIES.get(settings.AUTH_REFRESH_COOKIE_NAME)
        if not refresh_value:
            return Response({"detail": "Session expirée."}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = TokenRefreshSerializer(data={"refresh": refresh_value})
        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            response = Response({"detail": "Session expirée."}, status=status.HTTP_401_UNAUTHORIZED)
            _clear_refresh_cookie(response)
            return response

        data = dict(serializer.validated_data)
        rotated_refresh = data.pop("refresh", None)

        # Renvoyer aussi le profil dans la même réponse évite un second aller-retour /auth/me/
        # au chargement de chaque page. Le refresh vient d'être validé par SimpleJWT : le user_id
        # contenu dans ce jeton peut donc servir à reconstruire la session côté frontend.
        try:
            identity_token = RefreshToken(rotated_refresh or refresh_value)
            user_id = identity_token.get("user_id")
            user = User.objects.filter(pk=user_id, is_active=True).first()
        except Exception:
            user = None
        if user is None:
            response = Response({"detail": "Session expirée."}, status=status.HTTP_401_UNAUTHORIZED)
            _clear_refresh_cookie(response)
            return response

        data["user"] = UserSerializer(user).data
        response = Response(data, status=status.HTTP_200_OK)
        if rotated_refresh:
            _set_refresh_cookie(response, rotated_refresh)
        return response


def _blacklist_user_refresh_tokens(user):
    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)


class LogoutView(APIView):
    # La déconnexion doit fonctionner même lorsque l'access token vient d'expirer. Le refresh
    # HttpOnly est la source d'autorité pour révoquer la session, puis le cookie est supprimé.
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        if not _cookie_request_origin_allowed(request):
            return Response({"detail": "Origine non autorisée."}, status=status.HTTP_403_FORBIDDEN)
        refresh_value = request.COOKIES.get(settings.AUTH_REFRESH_COOKIE_NAME)
        if refresh_value:
            try:
                RefreshToken(refresh_value).blacklist()
            except Exception:
                pass
        response = Response(status=status.HTTP_204_NO_CONTENT)
        _clear_refresh_cookie(response)
        return response


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    throttle_classes = [AuthRateThrottle]
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        if not PlatformSettings.load().registration_enabled:
            return Response({"detail": "Les inscriptions sont temporairement désactivées par l'administrateur."}, status=403)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        try:
            from apps.notifications.email_services import queue_welcome_email
            transaction.on_commit(lambda user=user: queue_welcome_email(user))
        except Exception:
            pass
        refresh = EmailTokenObtainPairSerializer.get_token(user)
        response = Response(
            {
                "user": UserSerializer(user).data,
                "access": str(refresh.access_token),
            },
            status=status.HTTP_201_CREATED,
        )
        _set_refresh_cookie(response, str(refresh))
        return response


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class InstructorOverviewView(APIView):
    """Vue consolidée de l'activité d'un instructeur.

    Les chiffres sont calculés côté serveur afin que le dashboard n'ait pas à agréger
    plusieurs endpoints publics et ne puisse jamais mélanger les données d'un autre instructeur.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role not in (User.Role.INSTRUCTOR, User.Role.ADMIN):
            return Response({"detail": "Compte instructeur requis."}, status=403)

        from apps.catalog.models import Course, PDFProduct
        from apps.enrollments.models import CourseEnrollment, PDFPurchase
        from apps.formations.models import InteractiveFormation, FormationEnrollment, FormationSession
        from apps.reviews.models import Review, LessonComment

        instructor = request.user
        courses = Course.objects.filter(instructor=instructor)
        pdfs = PDFProduct.objects.filter(instructor=instructor)
        formations = InteractiveFormation.objects.filter(Q(instructor=instructor) | Q(co_instructor=instructor)).distinct()

        course_enrollments = CourseEnrollment.objects.filter(course__instructor=instructor)
        formation_enrollments = FormationEnrollment.objects.filter(formation__in=formations)
        pdf_purchases = PDFPurchase.objects.filter(pdf_product__instructor=instructor)
        student_ids = set(course_enrollments.values_list("user_id", flat=True))
        student_ids.update(formation_enrollments.values_list("user_id", flat=True))
        student_ids.update(pdf_purchases.values_list("user_id", flat=True))

        reviews = Review.objects.filter(Q(course__instructor=instructor) | Q(pdf_product__instructor=instructor))
        review_stats = reviews.aggregate(avg=Avg("rating"), count=Count("id"))
        questions = LessonComment.objects.filter(lesson__section__course__instructor=instructor, parent__isnull=True)
        upcoming = FormationSession.objects.filter(
            Q(formation__instructor=instructor) | Q(formation__co_instructor=instructor),
            completed=False, scheduled_at__gte=timezone.now(),
        ).select_related("formation").order_by("scheduled_at")[:5]

        recent_students = []
        for enrollment in course_enrollments.select_related("user", "course").order_by("-purchased_at")[:5]:
            recent_students.append({
                "user_id": enrollment.user_id,
                "name": enrollment.user.get_full_name() or enrollment.user.username,
                "email": enrollment.user.email,
                "content_type": "course",
                "content_title": enrollment.course.title,
                "progress_percent": enrollment.progress_percent,
                "acquired_at": enrollment.purchased_at,
            })

        recent_reviews = [
            {
                "id": r.id,
                "student": r.user.get_full_name() or r.user.username,
                "rating": r.rating,
                "comment": r.comment,
                "target_title": (r.course or r.pdf_product).title if (r.course or r.pdf_product) else "",
                "created_at": r.created_at,
            }
            for r in reviews.select_related("user", "course", "pdf_product").order_by("-created_at")[:5]
        ]

        return Response({
            "courses": courses.count(),
            "published_courses": courses.filter(published=True).count(),
            "pdfs": pdfs.count(),
            "published_pdfs": pdfs.filter(published=True).count(),
            "formations": formations.count(),
            "published_formations": formations.filter(published=True).count(),
            "unique_students": len(student_ids),
            "course_enrollments": course_enrollments.count(),
            "formation_enrollments": formation_enrollments.count(),
            "pdf_purchases": pdf_purchases.count(),
            "rating_avg": round(float(review_stats["avg"] or 0), 2),
            "reviews_count": review_stats["count"] or 0,
            "questions_count": questions.count(),
            "upcoming_sessions": [
                {
                    "id": session.id,
                    "formation_id": session.formation_id,
                    "formation_title": session.formation.title,
                    "session_number": session.session_number,
                    "scheduled_at": session.scheduled_at,
                    "duration_minutes": session.duration_minutes,
                    "started_at": session.started_at,
                }
                for session in upcoming
            ],
            "recent_students": recent_students,
            "recent_reviews": recent_reviews,
        })


class InstructorStudentsView(APIView):
    """Liste des apprenants/acheteurs rattachés aux contenus de l'instructeur."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role not in (User.Role.INSTRUCTOR, User.Role.ADMIN):
            return Response({"detail": "Compte instructeur requis."}, status=403)

        from apps.enrollments.models import CourseEnrollment, PDFPurchase
        from apps.formations.models import FormationEnrollment

        rows = []
        for e in CourseEnrollment.objects.filter(course__instructor=request.user).select_related("user", "course"):
            rows.append({
                "id": f"course-{e.id}",
                "user_id": e.user_id,
                "name": e.user.get_full_name() or e.user.username,
                "email": e.user.email,
                "content_type": "course",
                "content_id": e.course_id,
                "content_title": e.course.title,
                "progress_percent": e.progress_percent,
                "completed": e.completed,
                "acquired_at": e.purchased_at,
            })
        for e in FormationEnrollment.objects.filter(
            Q(formation__instructor=request.user) | Q(formation__co_instructor=request.user)
        ).select_related("user", "formation").distinct():
            rows.append({
                "id": f"formation-{e.id}",
                "user_id": e.user_id,
                "name": e.user.get_full_name() or e.user.username,
                "email": e.user.email,
                "content_type": "formation",
                "content_id": e.formation_id,
                "content_title": e.formation.title,
                "progress_percent": None,
                "completed": e.certificate_issued,
                "acquired_at": e.enrolled_at,
            })
        for e in PDFPurchase.objects.filter(pdf_product__instructor=request.user).select_related("user", "pdf_product"):
            rows.append({
                "id": f"pdf-{e.id}",
                "user_id": e.user_id,
                "name": e.user.get_full_name() or e.user.username,
                "email": e.user.email,
                "content_type": "pdf",
                "content_id": e.pdf_product_id,
                "content_title": e.pdf_product.title,
                "progress_percent": None,
                "completed": True,
                "acquired_at": e.purchased_at,
            })
        rows.sort(key=lambda r: r["acquired_at"], reverse=True)
        return Response({
            "count": len(rows),
            "unique_students": len({r["user_id"] for r in rows}),
            "results": rows,
        })


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        current_password = request.data.get("current_password", "")
        new_password = request.data.get("new_password", "")
        new_password2 = request.data.get("new_password2", "")
        if not request.user.check_password(current_password):
            return Response({"current_password": ["Mot de passe actuel incorrect."]}, status=400)
        if new_password != new_password2:
            return Response({"new_password2": ["Les mots de passe ne correspondent pas."]}, status=400)
        try:
            validate_password(new_password, user=request.user)
        except Exception as exc:
            return Response({"new_password": list(getattr(exc, "messages", [str(exc)]))}, status=400)
        request.user.set_password(new_password)
        request.user.save(update_fields=["password"])
        _blacklist_user_refresh_tokens(request.user)
        response = Response({"detail": "Mot de passe modifié avec succès. Reconnectez-vous sur vos appareils."})
        _clear_refresh_cookie(response)
        return response


class InstructorApplyView(APIView):
    """Dépôt et consultation de la demande instructeur du compte connecté.

    Un étudiant ne devient plus instructeur immédiatement : l'administrateur doit approuver
    explicitement la demande depuis le back-office.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role == User.Role.INSTRUCTOR:
            return Response({"status": InstructorApplication.Status.APPROVED, "already_instructor": True})
        application = InstructorApplication.objects.filter(user=request.user).first()
        if not application:
            return Response({"status": "none"})
        return Response(InstructorApplicationSerializer(application).data)

    def post(self, request):
        if request.user.role == User.Role.EMPLOYER:
            return Response({"detail": "Un compte entreprise / recruteur ne peut pas devenir instructeur. Utilisez un compte personnel apprenant pour ce parcours."}, status=403)
        if not PlatformSettings.load().instructor_applications_enabled and request.user.role != User.Role.ADMIN:
            return Response({"detail": "Les demandes instructeur sont temporairement désactivées."}, status=403)
        if request.user.role == User.Role.INSTRUCTOR:
            return Response({"detail": "Votre compte est déjà instructeur."}, status=400)

        domain = (request.data.get("domain") or "").strip()
        headline = (request.data.get("headline") or "").strip()
        message = (request.data.get("message") or "").strip()
        try:
            years_experience = max(0, int(request.data.get("years_experience", 0)))
        except (TypeError, ValueError):
            return Response({"years_experience": ["Valeur invalide."]}, status=400)
        if not domain:
            return Response({"domain": ["Ce champ est obligatoire."]}, status=400)

        application = InstructorApplication.objects.filter(user=request.user).first()
        if application and application.status == InstructorApplication.Status.PENDING:
            return Response(
                {"detail": "Une demande instructeur est déjà en attente de validation."},
                status=status.HTTP_409_CONFLICT,
            )

        if application:
            application.domain = domain
            application.years_experience = years_experience
            application.headline = headline
            application.message = message
            application.status = InstructorApplication.Status.PENDING
            application.review_note = ""
            application.reviewed_by = None
            application.reviewed_at = None
            application.save()
        else:
            application = InstructorApplication.objects.create(
                user=request.user, domain=domain, years_experience=years_experience,
                headline=headline, message=message,
            )
        return Response(InstructorApplicationSerializer(application).data, status=status.HTTP_201_CREATED)


class PasswordResetRequestView(APIView):
    throttle_classes = [PasswordResetRateThrottle]
    """Étape 1 : l'utilisateur saisit son email, on lui envoie un lien de réinitialisation.
    Pour ne jamais révéler si un email existe en base (sécurité), on répond toujours 200."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        generic_response = Response({
            "detail": "Si un compte existe avec cet email, un lien de réinitialisation a été envoyé."
        })

        if not email:
            return Response({"email": ["Ce champ est obligatoire."]}, status=400)

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return generic_response

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_url = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}"

        try:
            from apps.notifications.email_services import queue_password_reset_email
            delivery = queue_password_reset_email(user, reset_url)
        except Exception:
            delivery = None
        if delivery is None:
            send_mail(
                subject="Réinitialisation de votre mot de passe KalanPro",
                message=(
                    f"Bonjour {user.first_name or user.username},\n\n"
                    f"Cliquez sur ce lien pour choisir un nouveau mot de passe :\n{reset_url}\n\n"
                    f"Si vous n'êtes pas à l'origine de cette demande, ignorez cet email.\n\n"
                    f"L'équipe KalanPro"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )

        response_data = {"detail": "Si un compte existe avec cet email, un lien de réinitialisation a été envoyé."}
        # En développement (DEBUG=True), on renvoie aussi le lien directement : cela évite
        # d'avoir à configurer un vrai serveur SMTP pour tester le flux de bout en bout.
        # En production (DEBUG=False), le lien n'est JAMAIS renvoyé dans la réponse HTTP.
        if settings.DEBUG:
            response_data["dev_reset_url"] = reset_url
        return Response(response_data)


class PasswordResetConfirmView(APIView):
    throttle_classes = [PasswordResetRateThrottle]
    """Étape 2 : l'utilisateur choisit son nouveau mot de passe via le lien reçu."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        uidb64 = request.data.get("uid")
        token = request.data.get("token")
        new_password = request.data.get("new_password", "")
        new_password2 = request.data.get("new_password2", "")

        if new_password != new_password2:
            return Response({"new_password2": ["Les mots de passe ne correspondent pas."]}, status=400)

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({"detail": "Lien de réinitialisation invalide."}, status=400)

        if not default_token_generator.check_token(user, token):
            return Response({"detail": "Ce lien a expiré ou est invalide. Refaites une demande."}, status=400)

        try:
            validate_password(new_password, user=user)
        except Exception as exc:
            return Response({"new_password": list(getattr(exc, "messages", [str(exc)]))}, status=400)
        user.set_password(new_password)
        user.save(update_fields=["password"])
        _blacklist_user_refresh_tokens(user)
        return Response({"detail": "Mot de passe modifié avec succès. Vous pouvez vous connecter."})


class IsAdminRole(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == User.Role.ADMIN)


class AdminInstructorApplicationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InstructorApplicationAdminSerializer
    permission_classes = [IsAdminRole]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status"]
    search_fields = ["user__email", "user__first_name", "user__last_name", "domain", "headline"]
    ordering_fields = ["created_at", "updated_at", "reviewed_at", "years_experience"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return InstructorApplication.objects.select_related("user", "reviewed_by")

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def approve(self, request, pk=None):
        application = self.get_object()
        if application.status == InstructorApplication.Status.APPROVED:
            return Response(self.get_serializer(application).data)
        user = application.user
        user.domain = application.domain
        user.years_experience = application.years_experience
        user.headline = application.headline
        user.role = User.Role.INSTRUCTOR
        user.save(update_fields=["domain", "years_experience", "headline", "role"])
        application.status = InstructorApplication.Status.APPROVED
        application.review_note = (request.data.get("review_note") or "").strip()
        application.reviewed_by = request.user
        application.reviewed_at = timezone.now()
        application.save(update_fields=["status", "review_note", "reviewed_by", "reviewed_at", "updated_at"])
        return Response(self.get_serializer(application).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def reject(self, request, pk=None):
        application = self.get_object()
        if application.status == InstructorApplication.Status.APPROVED:
            return Response({"detail": "Une demande déjà approuvée ne peut pas être refusée. Modifiez le rôle du compte depuis Utilisateurs si nécessaire."}, status=400)
        if application.status == InstructorApplication.Status.REJECTED:
            return Response(self.get_serializer(application).data)
        application.status = InstructorApplication.Status.REJECTED
        application.review_note = (request.data.get("review_note") or "").strip()
        application.reviewed_by = request.user
        application.reviewed_at = timezone.now()
        application.save(update_fields=["status", "review_note", "reviewed_by", "reviewed_at", "updated_at"])
        return Response(self.get_serializer(application).data)


class AdminUserViewSet(viewsets.ModelViewSet):
    """Gestion des comptes depuis le back-office KalanPro.

    La suppression physique n'est pas exposée : un administrateur désactive un compte afin de
    conserver les historiques de commandes, présences et paiements.
    """
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminRole]
    http_method_names = ["get", "post", "patch", "head", "options"]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["role", "is_active"]
    search_fields = ["email", "username", "first_name", "last_name"]
    ordering_fields = ["date_joined", "last_login", "email", "role"]
    ordering = ["-date_joined"]

    def get_serializer_class(self):
        return AdminUserCreateSerializer if self.action == "create" else AdminUserSerializer

    def get_queryset(self):
        return User.objects.all()

    def partial_update(self, request, *args, **kwargs):
        target = self.get_object()
        requested_role = request.data.get("role", target.role)
        requested_active = request.data.get("is_active", target.is_active)

        if target.pk == request.user.pk and (requested_role != User.Role.ADMIN or requested_active is False):
            return Response({"detail": "Vous ne pouvez pas retirer vos propres droits administrateur ni désactiver votre compte ici."}, status=400)

        if target.role == User.Role.ADMIN and (requested_role != User.Role.ADMIN or requested_active is False):
            active_admins = User.objects.filter(role=User.Role.ADMIN, is_active=True).exclude(pk=target.pk).count()
            if active_admins == 0:
                return Response({"detail": "Au moins un administrateur actif doit rester sur la plateforme."}, status=400)

        previous_role = target.role
        with transaction.atomic():
            response = super().partial_update(request, *args, **kwargs)
            target.refresh_from_db(fields=["role", "is_active"])
            if previous_role == User.Role.EMPLOYER and (target.role != User.Role.EMPLOYER or not target.is_active):
                # Retirer le rôle recruteur doit retirer immédiatement ses capacités métier,
                # sans supprimer l'historique des offres/candidatures.
                from apps.opportunities.models import EmployerProfile, Opportunity
                employer = EmployerProfile.objects.filter(user=target).first()
                if employer:
                    employer.status = EmployerProfile.Status.SUSPENDED
                    employer.review_note = "Accès recruteur suspendu suite à une modification administrative du compte."
                    employer.reviewed_by = request.user
                    employer.reviewed_at = timezone.now()
                    employer.save(update_fields=["status", "review_note", "reviewed_by", "reviewed_at", "updated_at"])
                    Opportunity.objects.filter(employer=employer, status=Opportunity.Status.PUBLISHED).update(status=Opportunity.Status.CLOSED)
        return response


class PublicPlatformSettingsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        config = PlatformSettings.load()
        return Response({
            "site_name": config.site_name,
            "support_email": config.support_email,
            "registration_enabled": config.registration_enabled,
            "instructor_applications_enabled": config.instructor_applications_enabled,
            "pricing_enabled": config.pricing_enabled,
            "platform_commission_percent": config.platform_commission_percent,
            "instructor_pro_monthly_eur": config.instructor_pro_monthly_eur,
            "instructor_pro_commission_percent": config.instructor_pro_commission_percent,
            "mentor_commission_percent": config.mentor_commission_percent,
            "employer_free_active_jobs": config.employer_free_active_jobs,
            "employer_single_post_eur": config.employer_single_post_eur,
            "employer_pro_monthly_eur": config.employer_pro_monthly_eur,
            "employer_pro_active_jobs": config.employer_pro_active_jobs,
            "employer_business_monthly_eur": config.employer_business_monthly_eur,
            "employer_business_active_jobs": config.employer_business_active_jobs,
            "legal_company_name": config.legal_company_name,
            "legal_address": config.legal_address,
            "legal_country": config.legal_country,
            "legal_registration_number": config.legal_registration_number,
            "legal_tax_number": config.legal_tax_number,
            "privacy_email": config.privacy_email,
            "terms_updated_at": config.terms_updated_at,
            "privacy_updated_at": config.privacy_updated_at,
            "refund_policy_days": config.refund_policy_days,
            "certificate_verification_enabled": config.certificate_verification_enabled,
        })


class AdminPlatformSettingsView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        return Response(PlatformSettingsSerializer(PlatformSettings.load()).data)

    def patch(self, request):
        config = PlatformSettings.load()
        serializer = PlatformSettingsSerializer(config, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
