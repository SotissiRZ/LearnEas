import hmac
import hashlib
from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed


def password_fingerprint(user) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        user.password.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:24]


class PasswordBoundJWTAuthentication(JWTAuthentication):
    """Invalide immédiatement les access tokens après changement de mot de passe."""
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        claim = validated_token.get("pwd")
        if not claim or not hmac.compare_digest(str(claim), password_fingerprint(user)):
            raise AuthenticationFailed("Session expirée. Veuillez vous reconnecter.", code="token_not_valid")
        return user
