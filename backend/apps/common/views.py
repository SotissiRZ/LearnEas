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
from urllib.parse import quote, urlparse
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from apps.common.throttles import MediaRateThrottle
from apps.common.hls_media import rewrite_hls_playlist, unsign_hls_token


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
            response["Accept-Ranges"] = "bytes"
            response["Referrer-Policy"] = "no-referrer"
            return response

        content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
        is_video = content_type.startswith("video/")

        # Les vidéos LearnEas sont destinées au lecteur intégré. Une navigation directe
        # (nouvel onglet / iframe de téléchargement) est refusée lorsque le navigateur
        # l'identifie explicitement comme un document. Cela ne remplace pas un DRM, mais
        # élimine les voies de téléchargement proposées par l'interface et les navigations
        # directes les plus courantes tout en laissant fonctionner les requêtes <video>.
        fetch_dest = (request.headers.get("Sec-Fetch-Dest") or "").lower()
        if is_video and fetch_dest in {"document", "iframe", "object", "embed"}:
            return Response({"detail": "Cette vidéo doit être lue depuis le lecteur LearnEas."}, status=403)

        if getattr(settings, "USE_S3", False):
            if not default_storage.exists(name):
                return Response({"detail": "Fichier introuvable."}, status=404)
            parameters = {
                "ResponseContentDisposition": "inline",
                "ResponseCacheControl": "private, no-store",
                "ResponseContentType": content_type,
            } if is_video else {}
            try:
                storage_url = default_storage.url(name, parameters=parameters or None)
            except TypeError:
                storage_url = default_storage.url(name)
            response = redirect(storage_url)
            if is_video:
                response["X-Download-Options"] = "noopen"
                response["Cross-Origin-Resource-Policy"] = "same-site"
            return allow_embedding(response)

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
        response = HttpResponse(status=200, content_type=content_type)
        response["Content-Disposition"] = content_disposition_header(False, Path(name).name)
        if is_video:
            response["X-Download-Options"] = "noopen"
            response["Cross-Origin-Resource-Policy"] = "same-origin"
        # X-Accel-Redirect est une URI, pas un chemin système : les accents/espaces doivent être
        # percent-encodés, sinon nginx peut retourner un contenu invalide/404 alors que le fichier existe.
        response["X-Accel-Redirect"] = f"/_protected_media/{quote(name, safe='/')}"
        response["X-Accel-Buffering"] = "no"
        return allow_embedding(response)


@method_decorator(xframe_options_exempt, name="dispatch")
class HlsMediaView(APIView):
    """Sert les manifests/segments HLS privés avec des URL signées expirantes.

    Les manifests sont réécrits à la volée afin que chaque playlist et segment possède
    son propre jeton. Cela permet à hls.js/Safari de suivre les références relatives sans
    rendre le répertoire ``courses/hls`` public.
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [MediaRateThrottle]

    def get(self, request):
        token = request.query_params.get("token", "")
        try:
            name = unsign_hls_token(token, max_age=settings.HLS_MEDIA_TOKEN_MAX_AGE)
        except Exception:
            return Response({"detail": "Lien streaming invalide ou expiré."}, status=403)

        using_s3 = bool(getattr(settings, "USE_S3", False))
        # Sur S3/R2, éviter un HEAD `exists()` pour chaque segment : le stockage signé
        # répondra lui-même 404 si un objet a disparu. En local, le stat reste peu coûteux.
        if not using_s3 and not default_storage.exists(name):
            return Response({"detail": "Segment streaming introuvable."}, status=404)

        lower = name.lower()
        if lower.endswith(".m3u8"):
            content_type = "application/vnd.apple.mpegurl"
        elif lower.endswith(".ts"):
            content_type = "video/mp2t"
        elif lower.endswith(".aac"):
            content_type = "audio/aac"
        elif lower.endswith(".m4s"):
            content_type = "video/iso.segment"
        else:
            content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"

        if lower.endswith(".m3u8"):
            try:
                with default_storage.open(name, "rb") as handle:
                    body = handle.read().decode("utf-8")
                rewritten = rewrite_hls_playlist(name, body)
            except Exception:
                return Response({"detail": "Manifest streaming invalide."}, status=500)
            response = HttpResponse(rewritten, content_type="application/vnd.apple.mpegurl; charset=utf-8")
            response["Cache-Control"] = "private, no-store"
            response["Referrer-Policy"] = "no-referrer"
            response["X-Content-Type-Options"] = "nosniff"
            return response

        # Segments : déléguer les octets à nginx en local ou au stockage S3 via URL présignée.
        if using_s3:
            try:
                storage_url = default_storage.url(name)
            except Exception:
                return Response({"detail": "Segment streaming indisponible."}, status=404)
            response = redirect(storage_url)
            response["Cache-Control"] = "private, no-store"
            response["Referrer-Policy"] = "no-referrer"
            return response

        candidate = (Path(settings.MEDIA_ROOT) / name).resolve()
        media_root = Path(settings.MEDIA_ROOT).resolve()
        try:
            candidate.relative_to(media_root)
        except ValueError:
            return Response({"detail": "Chemin streaming invalide."}, status=403)
        if not candidate.is_file():
            return Response({"detail": "Segment streaming introuvable."}, status=404)

        response = HttpResponse(status=200, content_type=content_type)
        response["Content-Disposition"] = content_disposition_header(False, Path(name).name)
        response["X-Accel-Redirect"] = f"/_protected_media/{quote(name, safe='/')}"
        response["X-Accel-Buffering"] = "no"
        response["Cache-Control"] = "private, no-store"
        response["Accept-Ranges"] = "bytes"
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Download-Options"] = "noopen"
        response["Cross-Origin-Resource-Policy"] = "same-origin"
        response["Referrer-Policy"] = "no-referrer"
        return response
