from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Lesson
from .streaming import delete_hls_package_from_manifest


@receiver([post_save, post_delete], sender=Lesson)
def update_course_aggregates(sender, instance, **kwargs):
    course = instance.section.course
    course.refresh_aggregates()


@receiver(post_delete, sender=Lesson)
def delete_lesson_streaming_package(sender, instance, **kwargs):
    # Les segments HLS ne sont pas des FileField individuels : nettoyer explicitement le
    # paquet lorsque la leçon disparaît afin d'éviter de facturer du stockage orphelin.
    if instance.hls_master_path:
        delete_hls_package_from_manifest(instance.hls_master_path)
