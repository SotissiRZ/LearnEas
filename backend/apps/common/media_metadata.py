"""Extraction fiable des métadonnées des médias uploadés.

Les valeurs calculées ici sont la source de vérité : le client ne doit plus demander
à l'instructeur de saisir manuellement la durée d'une vidéo ou le nombre de pages.
"""
from __future__ import annotations

import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from pypdf import PdfReader
from rest_framework import serializers


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
    """Renvoie (chemin, temporaire_a_supprimer) pour ffprobe."""
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


def extract_video_duration_minutes(file_obj) -> int:
    """Extrait la durée réelle d'une vidéo locale avec ffprobe, arrondie à la minute supérieure."""
    if not file_obj:
        return 0
    path, temporary = _uploaded_file_path(file_obj)
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", path,
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if result.returncode != 0:
            raise ValueError(result.stderr.strip() or "ffprobe a échoué")
        seconds = float(result.stdout.strip())
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
