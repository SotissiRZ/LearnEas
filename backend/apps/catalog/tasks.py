from __future__ import annotations

from celery import shared_task
from django.conf import settings
from django.core.files.storage import default_storage
from django.utils import timezone

from apps.common.fields import ProtectedFileField
from apps.common.hls_media import sign_hls_path
from apps.common.media_metadata import prepare_video_upload
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
            streaming_error="Le HLS nécessite un fichier vidéo uploadé sur KalanPro.",
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
    """Prépare une vidéo de leçon hors requête HTTP.

    Pipeline unique :
      1. ouvre la source (locale ou S3/R2) ;
      2. normalise uniquement si le codec/conteneur n'est pas compatible navigateur ;
      3. calcule la durée réelle ;
      4. déclenche la génération HLS adaptative.

    Cette tâche est l'unique point d'entrée vidéo après upload afin que Gunicorn ne lance
    jamais ffprobe/ffmpeg sur le chemin critique d'une requête utilisateur.
    """
    lesson = Lesson.objects.select_related("section__course").get(pk=lesson_id)
    if not lesson.video_file:
        return {"lesson_id": lesson_id, "status": "no_file", "detail": "Aucun fichier vidéo à préparer."}

    Lesson.objects.filter(pk=lesson_id).update(
        streaming_status=StreamingStatus.PROCESSING,
        streaming_error="",
        streaming_updated_at=timezone.now(),
    )

    old_name = lesson.video_file.name
    try:
        normalized, duration_minutes = prepare_video_upload(lesson.video_file)
        was_normalized = normalized is not lesson.video_file

        if was_normalized:
            lesson.video_file.save(normalized.name, normalized, save=False)

        # Durée et compatibilité sont calculées sur la même copie locale de la source, ce qui
        # évite de retélécharger une grosse vidéo S3/R2 une seconde fois dans le worker.
        lesson.duration_minutes = duration_minutes
        lesson.streaming_status = StreamingStatus.PENDING
        lesson.streaming_error = ""
        lesson.streaming_updated_at = timezone.now()
        update_fields = ["duration_minutes", "streaming_status", "streaming_error", "streaming_updated_at"]
        if was_normalized:
            update_fields.append("video_file")
        lesson.save(update_fields=update_fields)

        if old_name and old_name != lesson.video_file.name:
            try:
                default_storage.delete(old_name)
            except Exception:
                pass

        if getattr(settings, "HLS_STREAMING_ENABLED", True):
            prepare_lesson_streaming.delay(lesson.id, force=True)
        else:
            Lesson.objects.filter(pk=lesson.id).update(
                streaming_status=StreamingStatus.READY,
                streaming_updated_at=timezone.now(),
            )

        return {
            "lesson_id": lesson_id,
            "status": "prepared",
            "video_file": ProtectedFileField().to_representation(lesson.video_file),
            "duration_minutes": duration_minutes,
        }
    except Exception as exc:
        message = str(exc).strip()[-2000:] or "Préparation vidéo échouée."
        Lesson.objects.filter(pk=lesson_id).update(
            streaming_status=StreamingStatus.FAILED,
            streaming_error=message,
            streaming_updated_at=timezone.now(),
        )
        raise

