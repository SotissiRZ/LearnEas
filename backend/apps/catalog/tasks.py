from __future__ import annotations

from celery import shared_task
from django.core.files.storage import default_storage

from apps.common.fields import ProtectedFileField
from apps.common.media_metadata import extract_video_duration_minutes, normalize_video_upload
from .models import Lesson


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
        return {
            "lesson_id": lesson_id,
            "status": "already_compatible",
            "video_file": ProtectedFileField().to_representation(lesson.video_file),
            "duration_minutes": lesson.duration_minutes,
        }

    duration_minutes = extract_video_duration_minutes(normalized)
    lesson.video_file.save(normalized.name, normalized, save=False)
    lesson.duration_minutes = duration_minutes
    lesson.save(update_fields=["video_file", "duration_minutes"])

    if old_name and old_name != lesson.video_file.name:
        try:
            default_storage.delete(old_name)
        except Exception:
            # Le nouveau fichier est déjà enregistré ; un ancien objet orphelin ne doit pas
            # faire échouer la réparation fonctionnelle.
            pass

    return {
        "lesson_id": lesson_id,
        "status": "converted",
        "video_file": ProtectedFileField().to_representation(lesson.video_file),
        "duration_minutes": lesson.duration_minutes,
    }
