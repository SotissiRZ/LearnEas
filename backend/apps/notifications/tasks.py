import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db.models import Max, Q
from django.utils import timezone

from apps.accounts.models import PlatformSettings
from .models import NotificationPreference, WhatsAppDelivery, EmailDelivery
from .services import queue_whatsapp_event, send_delivery
from .email_services import queue_email_event, send_email

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(OSError, TimeoutError), retry_backoff=True, retry_kwargs={"max_retries": 3})
def send_whatsapp_delivery(self, delivery_id):
    delivery = send_delivery(delivery_id)
    return getattr(delivery, "status", None)


@shared_task(bind=True, autoretry_for=(OSError, TimeoutError), retry_backoff=True, retry_kwargs={"max_retries": 3})
def send_email_delivery(self, delivery_id):
    delivery = send_email(delivery_id)
    return getattr(delivery, "status", None)


def _queue_live_channels(*, user, key, title, start_label, room_url, metadata):
    name = user.first_name or user.get_full_name() or user.username
    wa = queue_whatsapp_event(
        user=user,
        event_type=WhatsAppDelivery.EventType.LIVE,
        event_key=key,
        variables=[name, title, start_label, room_url],
        metadata=metadata,
    )
    email = queue_email_event(
        user=user,
        event_type=EmailDelivery.EventType.LIVE,
        event_key=f"email:{key}",
        subject=f"Rappel KalanPro · {title}",
        context={
            "eyebrow": "Rappel de séance",
            "title": "Votre séance commence bientôt",
            "greeting": f"Bonjour {name},",
            "intro": f"Votre séance « {title} » approche. Connectez-vous quelques minutes avant le début pour vérifier votre caméra, votre micro et votre connexion.",
            "details": [
                {"label": "Séance", "value": title},
                {"label": "Début", "value": start_label},
            ],
            "cta_label": "Rejoindre la salle KalanPro",
            "cta_url": room_url,
            "footer_note": "Sur mobile ou connexion limitée, privilégiez un réseau stable et fermez les applications inutiles.",
        },
        metadata=metadata,
    )
    return int(wa is not None) + int(email is not None)


@shared_task
def dispatch_whatsapp_live_reminders():
    """Compatibilité du nom historique : envoie désormais WhatsApp + email Resend."""
    config = PlatformSettings.load()
    if not ((config.whatsapp_enabled and getattr(settings, "WHATSAPP_ENABLED", False)) or (config.resend_enabled and getattr(settings, "RESEND_ENABLED", False))):
        return 0
    from apps.formations.models import FormationSession

    minutes = max(5, min(int(config.whatsapp_live_reminder_minutes or 30), 1440))
    now = timezone.now()
    target = now + timedelta(minutes=minutes)
    sessions = FormationSession.objects.filter(
        completed=False,
        scheduled_at__gte=target - timedelta(minutes=3),
        scheduled_at__lt=target + timedelta(minutes=4),
    ).select_related("formation").prefetch_related("mentorship_slot__bookings__user")
    count = 0
    for session in sessions:
        room_url = f"{settings.FRONTEND_URL.rstrip('/')}/live/session/{session.id}"
        try:
            mentor_slot = session.mentorship_slot
        except Exception:
            mentor_slot = None

        if mentor_slot is not None:
            try:
                from zoneinfo import ZoneInfo
                start_local = session.scheduled_at.astimezone(ZoneInfo(mentor_slot.offering.timezone))
            except Exception:
                start_local = timezone.localtime(session.scheduled_at)
            start_label = start_local.strftime("%d/%m/%Y %H:%M")
            confirmed = mentor_slot.bookings.filter(status="confirmed").select_related("user").first()
            if confirmed:
                user = confirmed.user
                title = f"Mentorat · {mentor_slot.offering.title}"
                count += _queue_live_channels(
                    user=user,
                    key=f"mentorship-live:{session.id}:{minutes}m:{user.id}",
                    title=title,
                    start_label=start_label,
                    room_url=room_url,
                    metadata={"session_id": session.id, "mentorship_booking_id": confirmed.id, "reminder_minutes": minutes},
                )

                mentor = mentor_slot.offering.instructor
                learner_name = user.get_full_name() or user.username
                count += _queue_live_channels(
                    user=mentor,
                    key=f"mentorship-live-mentor:{session.id}:{minutes}m:{mentor.id}",
                    title=f"{title} · {learner_name}",
                    start_label=start_label,
                    room_url=room_url,
                    metadata={"session_id": session.id, "mentorship_booking_id": confirmed.id, "reminder_minutes": minutes, "mentor": True},
                )
            continue

        start_label = timezone.localtime(session.scheduled_at).strftime("%d/%m/%Y %H:%M")
        enrollments = session.formation.enrollments.select_related("user").all()
        for enrollment in enrollments:
            user = enrollment.user
            count += _queue_live_channels(
                user=user,
                key=f"live:{session.id}:{minutes}m:{user.id}",
                title=session.formation.title,
                start_label=start_label,
                room_url=room_url,
                metadata={"session_id": session.id, "reminder_minutes": minutes},
            )
    return count


@shared_task
def dispatch_whatsapp_inactivity_reminders():
    """Compatibilité du nom historique : relances opt-in sur WhatsApp et/ou email."""
    config = PlatformSettings.load()
    if not ((config.whatsapp_enabled and getattr(settings, "WHATSAPP_ENABLED", False)) or (config.resend_enabled and getattr(settings, "RESEND_ENABLED", False))):
        return 0
    from apps.enrollments.models import CourseEnrollment

    days = max(2, min(int(config.whatsapp_inactivity_days or 4), 90))
    cutoff = timezone.now() - timedelta(days=days)
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
        pref, _ = NotificationPreference.objects.get_or_create(user=user)
        name = user.first_name or user.get_full_name() or user.username
        course_url = f"{settings.FRONTEND_URL.rstrip('/')}/learn/{enrollment.course.slug}"
        key = f"inactivity:{enrollment.id}:{year}-W{week:02d}"
        if pref.whatsapp_opt_in and pref.whatsapp_inactivity_enabled:
            delivery = queue_whatsapp_event(
                user=user,
                event_type=WhatsAppDelivery.EventType.INACTIVITY,
                event_key=key,
                variables=[name, enrollment.course.title, f"{enrollment.progress_percent}%", course_url],
                metadata={"course_enrollment_id": enrollment.id, "inactivity_days": days},
            )
            count += int(delivery is not None)
        if pref.email_enabled and pref.email_inactivity_enabled:
            delivery = queue_email_event(
                user=user,
                event_type=EmailDelivery.EventType.INACTIVITY,
                event_key=f"email:{key}",
                subject=f"Reprenez votre progression · {enrollment.course.title}",
                context={
                    "eyebrow": "Votre progression",
                    "title": "Continuez là où vous vous êtes arrêté",
                    "greeting": f"Bonjour {name},",
                    "intro": f"Votre formation « {enrollment.course.title} » vous attend. Quelques minutes aujourd'hui peuvent suffire pour reprendre le rythme.",
                    "details": [{"label": "Progression", "value": f"{enrollment.progress_percent}%"}],
                    "cta_label": "Reprendre la formation",
                    "cta_url": course_url,
                    "footer_note": "Vous pouvez désactiver les relances de progression dans vos préférences de notifications.",
                },
                metadata={"course_enrollment_id": enrollment.id, "inactivity_days": days},
            )
            count += int(delivery is not None)
    return count
