from __future__ import annotations

from celery import shared_task
from django.conf import settings
from django.core.files.storage import default_storage
from django.utils import timezone

from apps.common.fields import ProtectedFileField
from apps.common.hls_media import sign_hls_path
from apps.common.media_metadata import extract_video_duration_minutes, normalize_video_upload
from .models import Lesson, StreamingStatus
from .streaming import delete_hls_package_from_manifest, generate_lesson_hls


@shared_task(bind=True)
def prepare_lesson_streaming(self, lesson_id: int, force: bool = False):
    """Génère le HLS adaptatif et l'audio-only d'une leçon en arrière-plan."""
    lesson = Lesson.objects.select_related("section__course").get(pk=lesson_id)
    if not getattr(settings, "HLS_STREAMING_ENABLED", True):
        return {"lesson_id": lesson_id, "status": "disabled", "detail": "Streaming HLS désactivé."}
    if not lesson.video_file:
        Lesson.objects.filter(pk=lesson_id).update(
            streaming_status=StreamingStatus.FAILED,
            streaming_error="Le HLS nécessite un fichier vidéo uploadé sur LearnEas.",
            streaming_updated_at=timezone.now(),
        )
        return {"lesson_id": lesson_id, "status": "no_file", "detail": "Aucun fichier vidéo local."}
    if lesson.streaming_status == StreamingStatus.READY and lesson.hls_master_path and not force:
        return {
            "lesson_id": lesson_id,
            "status": "already_ready",
            "hls_url": sign_hls_path(lesson.hls_master_path),
            "audio_hls_url": sign_hls_path(lesson.audio_hls_path) if lesson.audio_hls_path else None,
            "variants": lesson.streaming_variants,
        }

    old_manifest = lesson.hls_master_path
    Lesson.objects.filter(pk=lesson_id).update(
        streaming_status=StreamingStatus.PROCESSING,
        streaming_error="",
        streaming_updated_at=timezone.now(),
    )
    try:
        package = generate_lesson_hls(lesson.video_file, lesson_id=lesson.id)
        Lesson.objects.filter(pk=lesson_id).update(
            hls_master_path=package["master_path"],
            audio_hls_path=package.get("audio_path") or "",
            streaming_variants=package.get("variants") or [],
            streaming_status=StreamingStatus.READY,
            streaming_error="",
            streaming_updated_at=timezone.now(),
        )
        if old_manifest and old_manifest != package["master_path"]:
            delete_hls_package_from_manifest(old_manifest)
        return {
            "lesson_id": lesson_id,
            "status": "ready",
            "hls_url": sign_hls_path(package["master_path"]),
            "audio_hls_url": sign_hls_path(package["audio_path"]) if package.get("audio_path") else None,
            "variants": package.get("variants") or [],
        }
    except Exception as exc:
        message = str(exc).strip()[-2000:] or "Préparation HLS échouée."
        Lesson.objects.filter(pk=lesson_id).update(
            streaming_status=StreamingStatus.FAILED,
            streaming_error=message,
            streaming_updated_at=timezone.now(),
        )
        raise


@shared_task(bind=True)
def normalize_lesson_video(self, lesson_id: int):
    """Répare une vidéo de leçon existante en la normalisant pour le lecteur web.

    La tâche s'exécute dans Celery pour ne pas bloquer Gunicorn pendant un transcodage long.
    """
    lesson = Lesson.objects.select_related("section__course").get(pk=lesson_id)
    if not lesson.video_file:
        return {"lesson_id": lesson_id, "status": "no_file", "detail": "Aucun fichier vidéo à convertir."}

    old_name = lesson.video_file.name
    normalized = normalize_video_upload(lesson.video_file)

    if normalized is lesson.video_file:
        # Même une vidéo déjà compatible peut ne pas avoir encore son paquet HLS (anciens cours).
        if getattr(settings, "HLS_STREAMING_ENABLED", True) and lesson.streaming_status != StreamingStatus.READY:
            prepare_lesson_streaming.delay(lesson.id)
        return {
            "lesson_id": lesson_id,
            "status": "already_compatible",
            "video_file": ProtectedFileField().to_representation(lesson.video_file),
            "duration_minutes": lesson.duration_minutes,
        }

    duration_minutes = extract_video_duration_minutes(normalized)
    lesson.video_file.save(normalized.name, normalized, save=False)
    lesson.duration_minutes = duration_minutes
    lesson.streaming_status = StreamingStatus.PENDING
    lesson.streaming_error = ""
    lesson.save(update_fields=["video_file", "duration_minutes", "streaming_status", "streaming_error"])

    if old_name and old_name != lesson.video_file.name:
        try:
            default_storage.delete(old_name)
        except Exception:
            pass

    if getattr(settings, "HLS_STREAMING_ENABLED", True):
        prepare_lesson_streaming.delay(lesson.id, force=True)

    return {
        "lesson_id": lesson_id,
        "status": "converted",
        "video_file": ProtectedFileField().to_representation(lesson.video_file),
        "duration_minutes": lesson.duration_minutes,
    }
