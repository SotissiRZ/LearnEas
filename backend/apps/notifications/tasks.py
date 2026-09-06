import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db.models import Max, Q
from django.utils import timezone

from apps.accounts.models import PlatformSettings
from .models import NotificationPreference, WhatsAppDelivery, EmailDelivery, InAppNotification
from .services import queue_whatsapp_event, queue_in_app_event, queue_recruitment_update, send_delivery
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
    in_app = queue_in_app_event(
        user=user, event_key=f"inapp:{key}", category=InAppNotification.Category.LIVE,
        event_type="live_reminder", title="Votre séance commence bientôt",
        body=f"{title} · {start_label}", action_url=room_url, metadata=metadata,
        priority=InAppNotification.Priority.HIGH,
    )
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
    return int(in_app is not None) + int(wa is not None) + int(email is not None)


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
        in_app = queue_in_app_event(
            user=user, event_key=f"inapp:{key}", category=InAppNotification.Category.LEARNING,
            event_type="learning_inactivity", title="Reprenez votre progression",
            body=f"{enrollment.course.title} · progression {enrollment.progress_percent}%",
            action_url=course_url, metadata={"course_enrollment_id": enrollment.id, "inactivity_days": days},
        )
        count += int(in_app is not None)
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


@shared_task
def dispatch_recruitment_interview_reminders():
    """Rappel idempotent des entretiens à ~60 minutes, tous canaux autorisés."""
    from apps.opportunities.models import RecruitmentInterview

    now = timezone.now()
    target = now + timedelta(minutes=60)
    rows = RecruitmentInterview.objects.filter(
        status=RecruitmentInterview.Status.SCHEDULED,
        scheduled_at__gte=target - timedelta(minutes=4),
        scheduled_at__lt=target + timedelta(minutes=5),
    ).select_related("application__candidate", "application__opportunity", "application__opportunity__employer")
    count = 0
    for interview in rows:
        user = interview.application.candidate
        opportunity = interview.application.opportunity
        when = timezone.localtime(interview.scheduled_at).strftime("%d/%m/%Y à %H:%M")
        action_url = f"{settings.FRONTEND_URL.rstrip('/')}/dashboard/student/opportunities"
        result = queue_recruitment_update(
            user=user, event_key=f"interview-reminder:{interview.id}:60m",
            title="Entretien dans environ 1 heure",
            body=f"{opportunity.title} · {opportunity.employer.company_name} · {when}",
            action_url=action_url,
            variables=[user.first_name or user.username, opportunity.title, when, action_url],
            metadata={"interview_id": interview.id, "application_id": interview.application_id, "reminder_minutes": 60},
            priority=InAppNotification.Priority.HIGH,
        )
        count += sum(int(v is not None) for v in result.values())
    return count


@shared_task
def dispatch_saved_talent_search_alerts():
    """Alerte les recruteurs Pro/Business lorsqu'un talent visible correspond à une recherche sauvegardée."""
    from apps.opportunities.models import CandidateProfile, EmployerProfile, SavedTalentSearch
    from apps.opportunities.services import (
        apply_talent_search_filters,
        employer_has_talent_pool_access,
        match_opportunity_breakdown,
    )

    now = timezone.now()
    searches = SavedTalentSearch.objects.filter(
        alerts_enabled=True,
        employer__status=EmployerProfile.Status.APPROVED,
    ).select_related("employer__user", "opportunity")[:500]
    notified = 0
    for saved in searches:
        employer = saved.employer
        if not employer_has_talent_pool_access(employer, now=now):
            continue
        since = saved.last_checked_at or saved.created_at
        cursor_id = int(saved.last_checked_candidate_id or 0)
        qs = CandidateProfile.objects.select_related("user").filter(
            is_searchable=True,
            updated_at__lte=now,
        ).filter(
            Q(updated_at__gt=since) | Q(updated_at=since, id__gt=cursor_id)
        )
        qs = apply_talent_search_filters(
            qs,
            search_text=saved.search_text,
            country=saved.country,
            availability=saved.availability,
            min_experience=saved.min_experience,
        )
        matches = []
        last_processed = None
        # Curseur composite (updated_at, id) : aucun talent n'est perdu lorsque plusieurs
        # profils partagent exactement le même timestamp ou lorsqu'un lot dépasse 300 lignes.
        for talent in qs.order_by("updated_at", "id")[:300]:
            last_processed = talent
            score = None
            if saved.opportunity_id:
                score = match_opportunity_breakdown(saved.opportunity, talent.user, profile=talent)["total"]
                if score < saved.min_match_score:
                    continue
            matches.append((talent, score))

        if last_processed is not None:
            saved.last_checked_at = last_processed.updated_at
            saved.last_checked_candidate_id = last_processed.id
        else:
            # Aucun candidat dans la fenêtre : avancer jusqu'à maintenant et remettre l'id à zéro.
            saved.last_checked_at = now
            saved.last_checked_candidate_id = 0
        saved.last_match_count = len(matches)
        saved.save(update_fields=[
            "last_checked_at", "last_checked_candidate_id", "last_match_count", "updated_at"
        ])
        if not matches:
            continue

        sample = ", ".join((row[0].user.get_full_name() or row[0].user.username) for row in matches[:3])
        suffix = "" if len(matches) <= 3 else f" et {len(matches) - 3} autre(s)"
        action_url = f"{settings.FRONTEND_URL.rstrip('/')}/dashboard/employer"
        score_label = f" · score ≥ {saved.min_match_score}%" if saved.opportunity_id and saved.min_match_score else ""
        key_stamp = f"{int((last_processed.updated_at if last_processed else now).timestamp())}:{getattr(last_processed, 'id', 0)}"
        result = queue_recruitment_update(
            user=employer.user,
            event_key=f"saved-talent-search:{saved.id}:{key_stamp}",
            title=f"Nouveaux talents · {saved.name}",
            body=f"{len(matches)} nouveau(x) profil(s) correspondent{score_label} : {sample}{suffix}.",
            action_url=action_url,
            variables=[employer.user.first_name or employer.user.username, saved.name, f"{len(matches)} nouveau(x) talent(s)", action_url],
            metadata={
                "saved_talent_search_id": saved.id,
                "match_count": len(matches),
                "opportunity_id": saved.opportunity_id,
            },
        )
        notified += int(any(value is not None for value in result.values()))
    return notified
