from pathlib import Path
import logging
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
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response
from apps.common.throttles import MediaRateThrottle, ClientTelemetryRateThrottle, AdminTestRateThrottle
from apps.common.hls_media import rewrite_hls_playlist, unsign_hls_token_payload
from apps.common.operations import build_operations_snapshot


logger = logging.getLogger(__name__)


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == "admin"
        )


class AdminOperationsView(APIView):
    permission_classes = [IsAdminRole]
    throttle_classes = [AdminTestRateThrottle]

    def get(self, request):
        scan_storage = str(request.query_params.get("scan_storage") or "").lower() in {"1", "true", "yes"}
        return Response(build_operations_snapshot(scan_storage=scan_storage))


class ClientErrorTelemetryView(APIView):
    """Journal minimal d'un crash frontend, volontairement sans stack/payload arbitraire."""
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ClientTelemetryRateThrottle]

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        digest = str(data.get("digest") or "")[:120]
        pathname = str(data.get("pathname") or "")[:500]
        error_name = str(data.get("name") or "Error")[:80]
        # Aucun message/stack n'est accepté : ils peuvent contenir des données personnelles.
        logger.warning(
            "frontend_error name=%s digest=%s pathname=%s",
            error_name,
            digest or "-",
            pathname or "-",
            extra={"path": pathname or "-"},
        )
        return Response(status=204)

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
            # Un média signé peut être affiché dans le lecteur KalanPro, sans rendre
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

        # Les vidéos KalanPro sont destinées au lecteur intégré. Une navigation directe
        # (nouvel onglet / iframe de téléchargement) est refusée lorsque le navigateur
        # l'identifie explicitement comme un document. Cela ne remplace pas un DRM, mais
        # élimine les voies de téléchargement proposées par l'interface et les navigations
        # directes les plus courantes tout en laissant fonctionner les requêtes <video>.
        fetch_dest = (request.headers.get("Sec-Fetch-Dest") or "").lower()
        if is_video and fetch_dest in {"document", "iframe", "object", "embed"}:
            return Response({"detail": "Cette vidéo doit être lue depuis le lecteur KalanPro."}, status=403)

        if getattr(settings, "USE_S3", False):
            # V89: pas de HEAD préalable sur S3/R2. L'URL présignée répondra elle-même 404
            # si l'objet a disparu, ce qui économise une requête réseau sur chaque ouverture.
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
            name, max_height = unsign_hls_token_payload(token, max_age=settings.HLS_MEDIA_TOKEN_MAX_AGE)
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
                rewritten = rewrite_hls_playlist(name, body, max_height=max_height)
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
                parameters = {
                    "ResponseCacheControl": f"private, max-age={settings.HLS_SEGMENT_CACHE_SECONDS}",
                    "ResponseContentType": content_type,
                    "ResponseContentDisposition": "inline",
                }
                try:
                    storage_url = default_storage.url(name, parameters=parameters)
                except TypeError:
                    storage_url = default_storage.url(name)
            except Exception:
                return Response({"detail": "Segment streaming indisponible."}, status=404)
            response = redirect(storage_url)
            response["Cache-Control"] = f"private, max-age={settings.HLS_SEGMENT_CACHE_SECONDS}"
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
        response["Cache-Control"] = f"private, max-age={settings.HLS_SEGMENT_CACHE_SECONDS}"
        response["Accept-Ranges"] = "bytes"
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Download-Options"] = "noopen"
        response["Cross-Origin-Resource-Policy"] = "same-origin"
        response["Referrer-Policy"] = "no-referrer"
        return response
