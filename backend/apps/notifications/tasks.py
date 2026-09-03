import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db.models import Max, Q
from django.utils import timezone

from apps.accounts.models import PlatformSettings
from .models import NotificationPreference, WhatsAppDelivery
from .services import queue_whatsapp_event, send_delivery

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(OSError, TimeoutError), retry_backoff=True, retry_kwargs={"max_retries": 3})
def send_whatsapp_delivery(self, delivery_id):
    delivery = send_delivery(delivery_id)
    return getattr(delivery, "status", None)


@shared_task
def dispatch_whatsapp_live_reminders():
    if not getattr(settings, "WHATSAPP_ENABLED", False):
        return 0
    config = PlatformSettings.load()
    if not config.whatsapp_enabled:
        return 0
    from apps.formations.models import FormationSession

    minutes = max(5, min(int(config.whatsapp_live_reminder_minutes or 30), 1440))
    now = timezone.now()
    # La tâche tourne toutes les 5 minutes : fenêtre légèrement chevauchante + event_key unique.
    target = now + timedelta(minutes=minutes)
    sessions = FormationSession.objects.filter(
        completed=False,
        scheduled_at__gte=target - timedelta(minutes=3),
        scheduled_at__lt=target + timedelta(minutes=4),
    ).select_related("formation")
    count = 0
    for session in sessions:
        start_label = timezone.localtime(session.scheduled_at).strftime("%d/%m/%Y %H:%M")
        room_url = f"{settings.FRONTEND_URL.rstrip('/')}/live/session/{session.id}"
        enrollments = session.formation.enrollments.select_related("user").all()
        for enrollment in enrollments:
            user = enrollment.user
            name = user.first_name or user.get_full_name() or user.username
            delivery = queue_whatsapp_event(
                user=user,
                event_type=WhatsAppDelivery.EventType.LIVE,
                event_key=f"live:{session.id}:{minutes}m:{user.id}",
                variables=[name, session.formation.title, start_label, room_url],
                metadata={"session_id": session.id, "reminder_minutes": minutes},
            )
            count += int(delivery is not None)
    return count


@shared_task
def dispatch_whatsapp_inactivity_reminders():
    if not getattr(settings, "WHATSAPP_ENABLED", False):
        return 0
    config = PlatformSettings.load()
    if not config.whatsapp_enabled:
        return 0
    from apps.enrollments.models import CourseEnrollment

    days = max(2, min(int(config.whatsapp_inactivity_days or 4), 90))
    cutoff = timezone.now() - timedelta(days=days)
    # Dernière activité = dernier LessonProgress, sinon date d'achat.
    enrollments = (
        CourseEnrollment.objects.filter(completed=False)
        .select_related("user", "course")
        .annotate(last_progress_at=Max("lesson_progress__updated_at"))
        .filter(Q(last_progress_at__lt=cutoff) | Q(last_progress_at__isnull=True, purchased_at__lt=cutoff))
    )
    year, week, _ = timezone.localdate().isocalendar()
    count = 0
    for enrollment in enrollments:
        user = enrollment.user
        try:
            pref = user.notification_preferences
        except NotificationPreference.DoesNotExist:
            continue
        if not (pref.whatsapp_opt_in and pref.whatsapp_inactivity_enabled):
            continue
        name = user.first_name or user.get_full_name() or user.username
        course_url = f"{settings.FRONTEND_URL.rstrip('/')}/learn/{enrollment.course.slug}"
        delivery = queue_whatsapp_event(
            user=user,
            event_type=WhatsAppDelivery.EventType.INACTIVITY,
            event_key=f"inactivity:{enrollment.id}:{year}-W{week:02d}",
            variables=[name, enrollment.course.title, f"{enrollment.progress_percent}%", course_url],
            metadata={"course_enrollment_id": enrollment.id, "inactivity_days": days},
        )
        count += int(delivery is not None)
    return count
