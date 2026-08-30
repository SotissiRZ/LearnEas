from pathlib import Path
from django.conf import settings
from django.core import signing
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from apps.common.throttles import MediaRateThrottle

class PrivateMediaView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [MediaRateThrottle]

    def get(self, request):
        token = request.query_params.get("token", "")
        try:
            payload = signing.loads(token, salt="learneas.private-media", max_age=300)
            name = payload["name"]
        except Exception:
            return Response({"detail": "Lien média invalide ou expiré."}, status=403)
        candidate = (Path(settings.MEDIA_ROOT) / name).resolve()
        media_root = Path(settings.MEDIA_ROOT).resolve()
        if not str(candidate).startswith(str(media_root)) or not candidate.is_file():
            return Response({"detail": "Fichier introuvable."}, status=404)
        response = Response(status=200)
        response["X-Accel-Redirect"] = f"/_protected_media/{name}"
        response["Cache-Control"] = "private, no-store"
        return response
