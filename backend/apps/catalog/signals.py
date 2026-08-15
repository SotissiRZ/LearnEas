from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Lesson


@receiver([post_save, post_delete], sender=Lesson)
def update_course_aggregates(sender, instance, **kwargs):
    course = instance.section.course
    course.refresh_aggregates()
