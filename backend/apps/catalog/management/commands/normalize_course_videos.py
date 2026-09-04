from __future__ import annotations

import math
import os
import shutil
import tempfile
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand

from apps.catalog.models import Lesson
from apps.common.media_metadata import browser_video_compatibility, probe_video_path
from apps.common.media_metadata import _run_ffmpeg_normalization


class Command(BaseCommand):
    help = (
        "Analyse les vidéos de leçons déjà stockées et convertit les fichiers incompatibles "
        "vers MP4 H.264/AAC pour le lecteur HTML5 KalanPro."
    )

    def add_arguments(self, parser):
        parser.add_argument("--lesson-id", type=int, default=None, help="Ne traiter qu'une leçon précise.")
        parser.add_argument("--dry-run", action="store_true", help="Analyser sans modifier les fichiers.")
        parser.add_argument("--force", action="store_true", help="Réencoder même une vidéo déjà compatible.")

    def handle(self, *args, **options):
        queryset = Lesson.objects.exclude(video_file="").exclude(video_file__isnull=True).order_by("id")
        if options["lesson_id"]:
            queryset = queryset.filter(id=options["lesson_id"])

        total = queryset.count()
        if total == 0:
            self.stdout.write(self.style.WARNING("Aucune vidéo uploadée à analyser."))
            return

        self.stdout.write(f"Analyse de {total} vidéo(s) de cours...")
        converted = 0
        skipped = 0
        failed = 0

        for lesson in queryset.iterator():
            field = lesson.video_file
            old_name = field.name
            source_path = None
            source_temp = False
            output_path = None
            try:
                try:
                    source_path = field.path
                    if not os.path.isfile(source_path):
                        raise FileNotFoundError(source_path)
                except (AttributeError, NotImplementedError, FileNotFoundError):
                    suffix = Path(old_name).suffix or ".bin"
                    fd, source_path = tempfile.mkstemp(prefix="learneas-existing-", suffix=suffix)
                    os.close(fd)
                    source_temp = True
                    with field.storage.open(old_name, "rb") as src, open(source_path, "wb") as dst:
                        shutil.copyfileobj(src, dst, length=1024 * 1024)

                compatible, info = browser_video_compatibility(source_path, filename=old_name)
                codec_label = f"{info.get('video_codec') or '?'} / {info.get('audio_codec') or 'sans audio'} / {info.get('pixel_format') or '?'}"
                if compatible and not options["force"]:
                    skipped += 1
                    self.stdout.write(self.style.SUCCESS(f"  ✓ leçon {lesson.id}: compatible ({codec_label}) — {old_name}"))
                    continue

                if options["dry_run"]:
                    converted += 1
                    self.stdout.write(self.style.WARNING(f"  • leçon {lesson.id}: à convertir ({codec_label}) — {old_name}"))
                    continue

                fd, output_path = tempfile.mkstemp(prefix="learneas-existing-web-", suffix=".mp4")
                os.close(fd)
                _run_ffmpeg_normalization(source_path, output_path)
                normalized_info = probe_video_path(output_path)
                duration = float(normalized_info.get("duration_seconds") or 0)
                duration_minutes = max(1, math.ceil(duration / 60)) if duration > 0 else lesson.duration_minutes

                stem = Path(old_name).stem
                new_basename = f"{stem}-web.mp4"
                with open(output_path, "rb") as converted_file:
                    # FieldFile.save applique automatiquement upload_to="courses/videos/".
                    field.save(new_basename, File(converted_file), save=False)
                lesson.duration_minutes = duration_minutes
                lesson.save(update_fields=["video_file", "duration_minutes"])

                # Ne supprimer l'original qu'après succès DB + stockage.
                if old_name and old_name != lesson.video_file.name:
                    try:
                        field.storage.delete(old_name)
                    except Exception as cleanup_exc:
                        self.stderr.write(f"    ancien fichier non supprimé ({cleanup_exc})")

                converted += 1
                self.stdout.write(self.style.SUCCESS(
                    f"  ✓ leçon {lesson.id}: convertie en H.264/AAC — {lesson.video_file.name}"
                ))
            except Exception as exc:
                failed += 1
                self.stderr.write(self.style.ERROR(f"  ✗ leçon {lesson.id}: {exc}"))
            finally:
                if source_temp and source_path:
                    try:
                        os.unlink(source_path)
                    except OSError:
                        pass
                if output_path:
                    try:
                        os.unlink(output_path)
                    except OSError:
                        pass

        self.stdout.write("")
        self.stdout.write(
            f"Terminé : {converted} convertie(s)/à convertir, {skipped} déjà compatible(s), {failed} échec(s)."
        )
        if options["dry_run"]:
            self.stdout.write("Relancez sans --dry-run pour appliquer les conversions.")
