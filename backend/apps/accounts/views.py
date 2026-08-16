from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.conf import settings
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .serializers import RegisterSerializer, UserSerializer

User = get_user_model()


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["full_name"] = user.get_full_name() or user.username
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


class LoginView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_201_CREATED,
        )


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class InstructorApplyView(APIView):
    """Permet à un admin (ou à un instructeur invité) d'être créé — dans le nouveau
    paradigme, tout utilisateur peut demander à devenir instructeur ; validation admin."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.role == User.Role.INSTRUCTOR:
            return Response({"detail": "Déjà instructeur."}, status=400)
        user.domain = request.data.get("domain", "")
        user.years_experience = request.data.get("years_experience", 0)
        user.headline = request.data.get("headline", "")
        user.role = User.Role.INSTRUCTOR
        user.save()
        return Response(UserSerializer(user).data)


class PasswordResetRequestView(APIView):
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

        send_mail(
            subject="Réinitialisation de votre mot de passe LearnEas",
            message=(
                f"Bonjour {user.first_name or user.username},\n\n"
                f"Cliquez sur ce lien pour choisir un nouveau mot de passe :\n{reset_url}\n\n"
                f"Si vous n'êtes pas à l'origine de cette demande, ignorez cet email.\n\n"
                f"L'équipe LearnEas"
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
    """Étape 2 : l'utilisateur choisit son nouveau mot de passe via le lien reçu."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        uidb64 = request.data.get("uid")
        token = request.data.get("token")
        new_password = request.data.get("new_password", "")
        new_password2 = request.data.get("new_password2", "")

        if len(new_password) < 8:
            return Response({"new_password": ["Doit contenir au moins 8 caractères."]}, status=400)
        if new_password != new_password2:
            return Response({"new_password2": ["Les mots de passe ne correspondent pas."]}, status=400)

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({"detail": "Lien de réinitialisation invalide."}, status=400)

        if not default_token_generator.check_token(user, token):
            return Response({"detail": "Ce lien a expiré ou est invalide. Refaites une demande."}, status=400)

        user.set_password(new_password)
        user.save()
        return Response({"detail": "Mot de passe modifié avec succès. Vous pouvez vous connecter."})
