from pathlib import Path
from django.conf import settings
from django.core import signing
from django.core.files.storage import default_storage
from django.shortcuts import redirect
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from apps.common.throttles import MediaRateThrottle


class PrivateMediaView(APIView):
    """Résout un jeton signé de courte durée vers un média privé.

    En Docker local, nginx sert le fichier via X-Accel-Redirect. Avec un stockage
    S3-compatible, Django renvoie une redirection vers une URL présignée expirant rapidement.
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [MediaRateThrottle]

    def get(self, request):
        token = request.query_params.get("token", "")
        try:
            payload = signing.loads(token, salt="learneas.private-media", max_age=300)
            name = str(payload["name"])
        except Exception:
            return Response({"detail": "Lien média invalide ou expiré."}, status=403)
        if not name or name.startswith("/") or ".." in Path(name).parts:
            return Response({"detail": "Chemin média invalide."}, status=403)

        if getattr(settings, "USE_S3", False):
            if not default_storage.exists(name):
                return Response({"detail": "Fichier introuvable."}, status=404)
            response = redirect(default_storage.url(name))
            response["Cache-Control"] = "private, no-store"
            response["Referrer-Policy"] = "no-referrer"
            return response

        candidate = (Path(settings.MEDIA_ROOT) / name).resolve()
        media_root = Path(settings.MEDIA_ROOT).resolve()
        try:
            candidate.relative_to(media_root)
        except ValueError:
            return Response({"detail": "Chemin média invalide."}, status=403)
        if not candidate.is_file():
            return Response({"detail": "Fichier introuvable."}, status=404)
        response = Response(status=200)
        response["X-Accel-Redirect"] = f"/_protected_media/{name}"
        response["Cache-Control"] = "private, no-store"
        return response
