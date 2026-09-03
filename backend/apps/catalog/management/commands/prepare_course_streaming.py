from django.core.management.base import BaseCommand

from apps.catalog.models import Lesson, StreamingStatus
from apps.catalog.tasks import prepare_lesson_streaming


class Command(BaseCommand):
    help = "Prépare le HLS adaptatif des vidéos de cours existantes via Celery."

    def add_arguments(self, parser):
        parser.add_argument("--course-id", type=int, default=None)
        parser.add_argument("--force", action="store_true")
        parser.add_argument("--sync", action="store_true", help="Exécute immédiatement au lieu de passer par Celery.")
        parser.add_argument("--limit", type=int, default=0)

    def handle(self, *args, **options):
        qs = Lesson.objects.exclude(video_file="").exclude(video_file__isnull=True).order_by("id")
        if options["course_id"]:
            qs = qs.filter(section__course_id=options["course_id"])
        if not options["force"]:
            qs = qs.exclude(streaming_status=StreamingStatus.READY)
        if options["limit"] > 0:
            qs = qs[: options["limit"]]

        count = 0
        for lesson in qs:
            count += 1
            if options["sync"]:
                self.stdout.write(f"Préparation HLS leçon {lesson.id} — {lesson.title}")
                prepare_lesson_streaming.run(lesson.id, force=options["force"])
            else:
                task = prepare_lesson_streaming.delay(lesson.id, force=options["force"])
                self.stdout.write(f"HLS en file: leçon {lesson.id} — tâche {task.id}")
        self.stdout.write(self.style.SUCCESS(f"{count} leçon(s) traitée(s)/mise(s) en file."))
