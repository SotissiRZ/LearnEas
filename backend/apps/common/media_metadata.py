"""Extraction et normalisation fiables des médias uploadés.

Les valeurs calculées ici sont la source de vérité : le client ne doit plus demander
à l'instructeur de saisir manuellement la durée d'une vidéo ou le nombre de pages.

Les navigateurs n'acceptent pas tous les codecs contenus dans un fichier ``.mp4``/``.mov``.
KalanPro normalise donc automatiquement les uploads incompatibles vers un MP4 H.264/AAC
(yuv420p) afin que le lecteur fonctionne de façon prévisible sur Chrome, Edge, Firefox,
Safari, Android et iOS.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.files.uploadedfile import TemporaryUploadedFile
from pypdf import PdfReader
from rest_framework import serializers


BROWSER_SAFE_VIDEO_CODEC = "h264"
BROWSER_SAFE_AUDIO_CODECS = {None, "aac"}
BROWSER_SAFE_PIXEL_FORMATS = {"yuv420p", "yuvj420p"}


def _reset_stream(file_obj, position: int | None) -> None:
    try:
        file_obj.seek(position or 0)
    except (AttributeError, OSError):
        pass


def extract_pdf_page_count(file_obj) -> int:
    """Retourne le nombre de pages d'un PDF uploadé et remet le curseur à sa place."""
    if not file_obj:
        return 0
    position = None
    try:
        position = file_obj.tell()
    except (AttributeError, OSError):
        pass
    try:
        reader = PdfReader(file_obj)
        count = len(reader.pages)
        if count <= 0:
            raise ValueError("PDF sans page")
        return count
    except Exception as exc:
        raise serializers.ValidationError({"file": "Impossible de lire ce PDF ou d'en extraire le nombre de pages."}) from exc
    finally:
        _reset_stream(file_obj, position)


def _uploaded_file_path(file_obj) -> tuple[str, bool]:
    """Renvoie ``(chemin, temporaire_a_supprimer)`` pour ffprobe/ffmpeg."""
    try:
        path = file_obj.temporary_file_path()
        if path and os.path.exists(path):
            return path, False
    except (AttributeError, OSError):
        pass

    suffix = Path(getattr(file_obj, "name", "video.bin")).suffix or ".bin"
    fd, path = tempfile.mkstemp(prefix="learneas-video-", suffix=suffix)
    os.close(fd)
    position = None
    try:
        try:
            position = file_obj.tell()
            file_obj.seek(0)
        except (AttributeError, OSError):
            pass
        with open(path, "wb") as dest:
            chunks = getattr(file_obj, "chunks", None)
            if callable(chunks):
                for chunk in chunks():
                    dest.write(chunk)
            else:
                shutil.copyfileobj(file_obj, dest)
    finally:
        _reset_stream(file_obj, position)
    return path, True


def probe_video_path(path: str | os.PathLike[str]) -> dict[str, Any]:
    """Retourne les métadonnées codecs utiles d'un fichier vidéo avec ffprobe.

    Lève ``ValueError`` si le fichier n'est pas une vidéo exploitable.
    """
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=format_name,duration:stream=index,codec_type,codec_name,pix_fmt,width,height",
            "-of", "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=getattr(settings, "VIDEO_PROBE_TIMEOUT_SECONDS", 120),
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or "ffprobe a échoué")
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError("Réponse ffprobe invalide") from exc

    streams = payload.get("streams") or []
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if not video_stream:
        raise ValueError("Aucune piste vidéo détectée")

    format_data = payload.get("format") or {}
    try:
        duration = float(format_data.get("duration") or 0)
    except (TypeError, ValueError):
        duration = 0.0

    return {
        "format_name": str(format_data.get("format_name") or ""),
        "duration_seconds": duration,
        "video_codec": str(video_stream.get("codec_name") or "").lower() or None,
        "pixel_format": str(video_stream.get("pix_fmt") or "").lower() or None,
        "width": int(video_stream.get("width") or 0),
        "height": int(video_stream.get("height") or 0),
        "audio_codec": (str(audio_stream.get("codec_name") or "").lower() or None) if audio_stream else None,
        "has_audio": bool(audio_stream),
    }


def browser_video_compatibility(path: str | os.PathLike[str], *, filename: str | None = None) -> tuple[bool, dict[str, Any]]:
    """Détermine si un fichier est directement lisible de manière fiable dans les navigateurs.

    On retient volontairement un sous-ensemble très compatible : conteneur MP4, H.264,
    yuv420p et audio AAC (ou absence de piste audio). Les autres formats peuvent fonctionner
    sur certains navigateurs, mais sont normalisés pour éviter les erreurs MEDIA_ERR_SRC_NOT_SUPPORTED.
    """
    info = probe_video_path(path)
    suffix = Path(filename or str(path)).suffix.lower()
    formats = {part.strip().lower() for part in str(info.get("format_name") or "").split(",") if part.strip()}
    is_mp4_container = suffix == ".mp4" and bool(formats.intersection({"mp4", "mov"}))
    video_ok = info.get("video_codec") == BROWSER_SAFE_VIDEO_CODEC
    pix_fmt = info.get("pixel_format")
    pixel_ok = pix_fmt in BROWSER_SAFE_PIXEL_FORMATS
    audio_ok = info.get("audio_codec") in BROWSER_SAFE_AUDIO_CODECS
    return bool(is_mp4_container and video_ok and pixel_ok and audio_ok), info


def _run_ffmpeg_normalization(source_path: str, output_path: str) -> None:
    """Transcode une vidéo en MP4 H.264/AAC universellement lisible."""
    timeout = getattr(settings, "VIDEO_TRANSCODE_TIMEOUT_SECONDS", 3600)
    preset = getattr(settings, "VIDEO_TRANSCODE_PRESET", "veryfast")
    crf = str(getattr(settings, "VIDEO_TRANSCODE_CRF", 22))
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", source_path,
        "-map", "0:v:0",
        "-map", "0:a:0?",
        "-c:v", "libx264",
        "-preset", str(preset),
        "-crf", crf,
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ac", "2",
        "-movflags", "+faststart",
        output_path,
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0 or not os.path.exists(output_path) or os.path.getsize(output_path) <= 0:
        raise ValueError(result.stderr.strip() or "ffmpeg n'a pas produit de fichier vidéo valide")


def _duration_minutes_from_info(info: dict[str, Any]) -> int:
    try:
        seconds = float(info.get("duration_seconds") or 0)
    except (TypeError, ValueError):
        seconds = 0.0
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError("durée invalide")
    return max(1, math.ceil(seconds / 60))


def prepare_video_upload(file_obj) -> tuple[Any, int]:
    """Prépare une vidéo dans un worker et renvoie ``(fichier, durée_minutes)``.

    Le fichier distant éventuel (S3/R2) n'est matérialisé qu'une seule fois sur disque local.
    La même copie sert à ffprobe, à la vérification de compatibilité et, si nécessaire, à ffmpeg.
    C'est important pour les vidéos de plusieurs Go : le worker ne doit pas télécharger deux fois
    la source depuis le bucket uniquement pour calculer sa durée.
    """
    if not file_obj:
        return file_obj, 0

    source_path, source_is_temp = _uploaded_file_path(file_obj)
    output_fd = None
    output_path = None
    try:
        if getattr(settings, "VIDEO_NORMALIZATION_ENABLED", True):
            compatible, source_info = browser_video_compatibility(
                source_path, filename=getattr(file_obj, "name", None)
            )
        else:
            source_info = probe_video_path(source_path)
            compatible = True

        try:
            duration_minutes = _duration_minutes_from_info(source_info)
        except ValueError:
            duration_minutes = 0
        if compatible:
            if duration_minutes <= 0:
                raise ValueError("durée invalide")
            return file_obj, duration_minutes

        output_fd, output_path = tempfile.mkstemp(prefix="learneas-normalized-", suffix=".mp4")
        os.close(output_fd)
        output_fd = None
        _run_ffmpeg_normalization(source_path, output_path)

        max_bytes = int(getattr(settings, "MAX_VIDEO_UPLOAD_MB", 2048)) * 1024 * 1024
        normalized_size = os.path.getsize(output_path)
        if normalized_size > max_bytes:
            raise serializers.ValidationError({
                "video_file": f"Après conversion web, la vidéo dépasse la limite de {max_bytes // (1024 * 1024)} Mo."
            })

        # Si le conteneur source ne fournissait pas une durée exploitable, vérifier la sortie.
        # (Normalement source_info suffit et évite un second ffprobe.)
        if duration_minutes <= 0:
            duration_minutes = _duration_minutes_from_info(probe_video_path(output_path))

        original_name = Path(getattr(file_obj, "name", "video.mp4"))
        normalized_name = f"{original_name.stem}.mp4"
        normalized = TemporaryUploadedFile(
            name=normalized_name,
            content_type="video/mp4",
            size=normalized_size,
            charset=None,
        )
        with open(output_path, "rb") as src:
            shutil.copyfileobj(src, normalized.file, length=1024 * 1024)
        normalized.file.flush()
        normalized.seek(0)
        normalized.size = normalized_size
        return normalized, duration_minutes
    except serializers.ValidationError:
        raise
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError) as exc:
        raise serializers.ValidationError({
            "video_file": (
                "Cette vidéo ne peut pas être préparée pour le lecteur web. "
                "Vérifiez qu'elle contient une piste vidéo valide ; KalanPro accepte puis convertit "
                "automatiquement MP4, MOV, M4V et WebM vers H.264/AAC."
            )
        }) from exc
    finally:
        if output_fd is not None:
            try:
                os.close(output_fd)
            except OSError:
                pass
        if output_path:
            try:
                os.unlink(output_path)
            except OSError:
                pass
        if source_is_temp:
            try:
                os.unlink(source_path)
            except OSError:
                pass


def normalize_video_upload(file_obj):
    """Compatibilité historique : normalise dans le contexte appelant et renvoie le fichier.

    Le pipeline KalanPro de production appelle désormais :func:`prepare_video_upload` depuis
    Celery ; cette fonction est conservée pour les appels internes/anciens sans dupliquer la logique.
    """
    prepared, _duration = prepare_video_upload(file_obj)
    return prepared

def extract_video_duration_minutes(file_obj) -> int:
    """Extrait la durée réelle d'une vidéo locale avec ffprobe, arrondie à la minute supérieure."""
    if not file_obj:
        return 0
    path, temporary = _uploaded_file_path(file_obj)
    try:
        info = probe_video_path(path)
        seconds = float(info.get("duration_seconds") or 0)
        if not math.isfinite(seconds) or seconds <= 0:
            raise ValueError("durée invalide")
        return max(1, math.ceil(seconds / 60))
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError) as exc:
        raise serializers.ValidationError({
            "video_file": "Impossible d'extraire automatiquement la durée de cette vidéo. Vérifiez le format du fichier."
        }) from exc
    finally:
        if temporary:
            try:
                os.unlink(path)
            except OSError:
                pass


_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_ZIP_MAGICS = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")


def _read_upload_head(file_obj, size=8192) -> bytes:
    position = None
    try:
        position = file_obj.tell()
    except (AttributeError, OSError):
        pass
    try:
        file_obj.seek(0)
        return file_obj.read(size) or b""
    finally:
        _reset_stream(file_obj, position)


def _validate_zip_structure(file_obj, *, suffix: str, field: str, max_bytes: int) -> None:
    position = None
    try:
        position = file_obj.tell()
    except (AttributeError, OSError):
        pass
    try:
        file_obj.seek(0)
        if not zipfile.is_zipfile(file_obj):
            raise serializers.ValidationError({field: "Le contenu du fichier ne correspond pas à son extension."})
        file_obj.seek(0)
        with zipfile.ZipFile(file_obj) as archive:
            infos = archive.infolist()
            names = {info.filename for info in infos}
            # Protection préventive : aucune archive déposée ne doit contenir de traversal de chemin
            # ni exploser à plusieurs gigaoctets si elle est inspectée ultérieurement.
            max_uncompressed = max(200 * 1024 * 1024, max_bytes * 20)
            if sum(max(0, info.file_size) for info in infos) > max_uncompressed:
                raise serializers.ValidationError({field: "Archive compressée anormalement volumineuse après extraction."})
            for info in infos:
                normalized = info.filename.replace("\\", "/")
                parts = [part for part in normalized.split("/") if part]
                if normalized.startswith("/") or ".." in parts:
                    raise serializers.ValidationError({field: "Archive contenant un chemin de fichier non sûr."})

            office_root = {".docx": "word/", ".xlsx": "xl/", ".pptx": "ppt/"}.get(suffix)
            if office_root:
                if "[Content_Types].xml" not in names or not any(name.startswith(office_root) for name in names):
                    raise serializers.ValidationError({field: "Le contenu Office ne correspond pas à son extension."})
    except zipfile.BadZipFile as exc:
        raise serializers.ValidationError({field: "Archive ZIP/Office invalide."}) from exc
    finally:
        _reset_stream(file_obj, position)


def validate_upload_signature(file_obj, *, suffix: str, field: str, max_bytes: int) -> None:
    """Vérifie les signatures structurelles des documents risqués sans faire confiance au MIME client."""
    head = _read_upload_head(file_obj)
    if suffix == ".pdf" and not head.startswith(b"%PDF-"):
        raise serializers.ValidationError({field: "Le contenu du fichier ne correspond pas à un PDF valide."})
    if suffix in {".doc", ".xls", ".ppt"} and not head.startswith(_OLE_MAGIC):
        raise serializers.ValidationError({field: "Le contenu du document Office ne correspond pas à son extension."})
    if suffix in {".docx", ".xlsx", ".pptx", ".zip"}:
        if not head.startswith(_ZIP_MAGICS):
            raise serializers.ValidationError({field: "Le contenu du fichier ne correspond pas à une archive ZIP/Office valide."})
        _validate_zip_structure(file_obj, suffix=suffix, field=field, max_bytes=max_bytes)
    if suffix in {".txt", ".csv", ".md", ".json"} and b"\x00" in head:
        raise serializers.ValidationError({field: "Ce fichier texte contient des données binaires inattendues."})
    if suffix == ".vtt":
        text_head = head.lstrip(b"\xef\xbb\xbf \t\r\n")
        if not text_head.startswith(b"WEBVTT"):
            raise serializers.ValidationError({field: "Fichier de sous-titres VTT invalide."})

    if suffix in {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip"}:
        from apps.common.malware import scan_upload
        scan_upload(file_obj, field=field)


def validate_upload_limits(file_obj, *, max_bytes: int, extensions: set[str], field: str = "file") -> None:
    """Validation serveur minimale commune : taille + extension normalisée.

    La validité structurelle est ensuite vérifiée par ImageField, PdfReader ou ffprobe selon le média.
    """
    if not file_obj:
        return
    size = int(getattr(file_obj, "size", 0) or 0)
    if size <= 0:
        raise serializers.ValidationError({field: "Le fichier est vide."})
    if size > max_bytes:
        raise serializers.ValidationError({field: f"Le fichier dépasse la limite de {max_bytes // (1024 * 1024)} Mo."})
    suffix = Path(getattr(file_obj, "name", "")).suffix.lower()
    if suffix not in extensions:
        allowed = ", ".join(sorted(extensions))
        raise serializers.ValidationError({field: f"Format non autorisé. Formats acceptés : {allowed}."})
    validate_upload_signature(file_obj, suffix=suffix, field=field, max_bytes=max_bytes)
