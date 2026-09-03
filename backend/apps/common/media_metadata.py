"""Extraction et normalisation fiables des médias uploadés.

Les valeurs calculées ici sont la source de vérité : le client ne doit plus demander
à l'instructeur de saisir manuellement la durée d'une vidéo ou le nombre de pages.

Les navigateurs n'acceptent pas tous les codecs contenus dans un fichier ``.mp4``/``.mov``.
LearnEas normalise donc automatiquement les uploads incompatibles vers un MP4 H.264/AAC
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


def normalize_video_upload(file_obj):
    """Normalise un upload vidéo si nécessaire et renvoie un UploadedFile prêt à sauvegarder.

    - MP4 H.264/AAC yuv420p : conservé tel quel (aucune perte ni délai).
    - MOV/M4V/WebM, HEVC/H.265, AV1, H.264 10-bit, audio incompatible, etc. :
      transcodés en MP4 H.264/AAC.

    Le transcodage est volontairement effectué côté serveur : accepter une extension ``.mp4``
    sans contrôler son codec conduit exactement à l'erreur navigateur « source non prise en charge ».
    """
    if not file_obj or not getattr(settings, "VIDEO_NORMALIZATION_ENABLED", True):
        return file_obj

    source_path, source_is_temp = _uploaded_file_path(file_obj)
    output_fd = None
    output_path = None
    try:
        compatible, _ = browser_video_compatibility(source_path, filename=getattr(file_obj, "name", None))
        if compatible:
            return file_obj

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
        return normalized
    except serializers.ValidationError:
        raise
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError) as exc:
        raise serializers.ValidationError({
            "video_file": (
                "Cette vidéo ne peut pas être préparée pour le lecteur web. "
                "Vérifiez qu'elle contient une piste vidéo valide ; LearnEas accepte puis convertit "
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
