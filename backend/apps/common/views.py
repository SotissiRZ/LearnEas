from pathlib import Path
import mimetypes
from django.conf import settings
from django.core import signing
from django.core.files.storage import default_storage
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.utils.http import content_disposition_header
from django.views.decorators.clickjacking import xframe_options_exempt
from urllib.parse import urlparse
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from apps.common.throttles import MediaRateThrottle


@method_decorator(xframe_options_exempt, name="dispatch")
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
            payload = signing.loads(token, salt="learneas.private-media", max_age=settings.PRIVATE_MEDIA_TOKEN_MAX_AGE)
            name = str(payload["name"])
        except Exception:
            return Response({"detail": "Lien média invalide ou expiré."}, status=403)
        if not name or name.startswith("/") or ".." in Path(name).parts:
            return Response({"detail": "Chemin média invalide."}, status=403)

        def allow_embedding(response):
            # Un média signé peut être affiché dans le lecteur LearnEas, sans rendre
            # l'ensemble du site intégrable dans une iframe. Les origines autorisées
            # sont limitées aux frontends explicitement configurés.
            origins = {"'self'"}
            for raw in [getattr(settings, "FRONTEND_URL", ""), *getattr(settings, "CORS_ALLOWED_ORIGINS", [])]:
                try:
                    parsed = urlparse(str(raw))
                    if parsed.scheme in {"http", "https"} and parsed.netloc:
                        origins.add(f"{parsed.scheme}://{parsed.netloc}")
                except Exception:
                    continue
            response["Content-Security-Policy"] = "frame-ancestors " + " ".join(sorted(origins))
            response["Cache-Control"] = "private, no-store"
            response["Referrer-Policy"] = "no-referrer"
            return response

        if getattr(settings, "USE_S3", False):
            if not default_storage.exists(name):
                return Response({"detail": "Fichier introuvable."}, status=404)
            return allow_embedding(redirect(default_storage.url(name)))

        candidate = (Path(settings.MEDIA_ROOT) / name).resolve()
        media_root = Path(settings.MEDIA_ROOT).resolve()
        try:
            candidate.relative_to(media_root)
        except ValueError:
            return Response({"detail": "Chemin média invalide."}, status=403)
        if not candidate.is_file():
            return Response({"detail": "Fichier introuvable."}, status=404)
        # Important : utiliser une HttpResponse Django et non une Response DRF.
        # Une réponse DRF sans corps est soumise au renderer négocié (JSON par défaut),
        # ce qui peut transformer le Content-Type du fichier servi par X-Accel-Redirect.
        # Le navigateur recevait alors les octets du PDF comme du texte brut (`%PDF`,
        # `endstream`, caractères illisibles) au lieu d'ouvrir son lecteur PDF natif.
        content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
        response = HttpResponse(status=200, content_type=content_type)
        response["Content-Disposition"] = content_disposition_header(False, Path(name).name)
        response["X-Accel-Redirect"] = f"/_protected_media/{name}"
        return allow_embedding(response)
