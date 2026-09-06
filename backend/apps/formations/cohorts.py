from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import FormationEnrollment, FormationWaitlistEntry, InteractiveFormation


def _active_checkout_reservations(formation):
    from apps.payments.models import FormationSeatReservation, Order
    now = timezone.now()
    return FormationSeatReservation.objects.filter(
        formation=formation,
        order__status=Order.Status.PENDING,
        expires_at__gt=now,
    ).count()


def _active_offers(formation, exclude_user_id=None):
    from apps.payments.models import FormationSeatReservation, Order
    now = timezone.now()
    reserved_users = FormationSeatReservation.objects.filter(
        formation=formation, order__status=Order.Status.PENDING, expires_at__gt=now
    ).values_list("user_id", flat=True)
    qs = FormationWaitlistEntry.objects.filter(
        formation=formation,
        status=FormationWaitlistEntry.Status.OFFERED,
        offer_expires_at__gt=now,
    ).exclude(user_id__in=reserved_users)
    if exclude_user_id:
        qs = qs.exclude(user_id=exclude_user_id)
    return qs.count()


def effective_seats_used(formation, *, exclude_waitlist_user_id=None):
    return (
        FormationEnrollment.objects.filter(formation=formation).count()
        + _active_checkout_reservations(formation)
        + _active_offers(formation, exclude_user_id=exclude_waitlist_user_id)
    )


def user_has_active_offer(user, formation):
    if not getattr(user, "is_authenticated", False):
        return False
    return FormationWaitlistEntry.objects.filter(
        formation=formation,
        user=user,
        status=FormationWaitlistEntry.Status.OFFERED,
        offer_expires_at__gt=timezone.now(),
    ).exists()


def can_checkout_formation(user, formation):
    if not formation.is_waitlist_open:
        return False
    exclude = user.id if user_has_active_offer(user, formation) else None
    return effective_seats_used(formation, exclude_waitlist_user_id=exclude) < formation.max_students


def _notify_offer(entry):
    try:
        from apps.notifications.models import InAppNotification
        from apps.notifications.services import queue_in_app_event
        queue_in_app_event(
            user=entry.user,
            event_key=f"inapp:cohort-waitlist-offer:{entry.id}:{int(entry.offered_at.timestamp()) if entry.offered_at else 0}",
            category=InAppNotification.Category.LEARNING,
            event_type="cohort_waitlist_offer",
            title="Une place s'est libérée",
            body=f"Vous avez une priorité temporaire pour rejoindre {entry.formation.title}.",
            action_url=f"{settings.FRONTEND_URL.rstrip('/')}/formations/{entry.formation.slug}",
            metadata={"formation_id": entry.formation_id, "waitlist_entry_id": entry.id},
            priority=InAppNotification.Priority.HIGH,
        )
    except Exception:
        # Le moteur de notification ne doit jamais bloquer la libération d'une place.
        pass


@transaction.atomic
def refresh_waitlist(formation_id):
    formation = InteractiveFormation.objects.select_for_update().get(pk=formation_id)
    now = timezone.now()
    expired = list(FormationWaitlistEntry.objects.select_for_update().filter(
        formation=formation,
        status=FormationWaitlistEntry.Status.OFFERED,
        offer_expires_at__lte=now,
    ))
    for entry in expired:
        entry.status = FormationWaitlistEntry.Status.EXPIRED
        entry.save(update_fields=["status", "updated_at"])

    if not formation.is_enrollment_open:
        return []

    ttl_hours = min(max(int(getattr(settings, "COHORT_WAITLIST_OFFER_HOURS", 24)), 1), 72)
    offered = []
    while effective_seats_used(formation) < formation.max_students:
        entry = FormationWaitlistEntry.objects.select_for_update().filter(
            formation=formation,
            status=FormationWaitlistEntry.Status.WAITING,
        ).order_by("created_at", "id").first()
        if not entry:
            break
        entry.status = FormationWaitlistEntry.Status.OFFERED
        entry.offered_at = now
        entry.offer_expires_at = now + timedelta(hours=ttl_hours)
        entry.save(update_fields=["status", "offered_at", "offer_expires_at", "updated_at"])
        offered.append(entry)
    for entry in offered:
        transaction.on_commit(lambda entry=entry: _notify_offer(entry))
    return offered


@transaction.atomic
def join_waitlist(user, formation):
    formation = InteractiveFormation.objects.select_for_update().get(pk=formation.pk)
    if FormationEnrollment.objects.filter(user=user, formation=formation).exists():
        raise ValueError("Vous êtes déjà inscrit à cette cohorte.")
    if not formation.is_waitlist_open:
        raise ValueError("La liste d'attente n'est pas disponible pour cette cohorte.")
    entry, _ = FormationWaitlistEntry.objects.select_for_update().get_or_create(
        formation=formation,
        user=user,
        defaults={"status": FormationWaitlistEntry.Status.WAITING},
    )
    # Un clic explicite sur « rejoindre » après expiration doit réinscrire immédiatement
    # l'utilisateur ; il ne doit pas être obligé de cliquer deux fois.
    if (
        entry.status == FormationWaitlistEntry.Status.OFFERED
        and entry.offer_expires_at
        and entry.offer_expires_at <= timezone.now()
    ):
        entry.status = FormationWaitlistEntry.Status.EXPIRED
    if entry.status in {FormationWaitlistEntry.Status.CANCELLED, FormationWaitlistEntry.Status.JOINED, FormationWaitlistEntry.Status.EXPIRED}:
        entry.status = FormationWaitlistEntry.Status.WAITING
        entry.offered_at = None
        entry.offer_expires_at = None
        entry.joined_at = None
        entry.save(update_fields=["status", "offered_at", "offer_expires_at", "joined_at", "updated_at"])
    refresh_waitlist(formation.id)
    entry.refresh_from_db()
    return entry


@transaction.atomic
def leave_waitlist(user, formation):
    entry = FormationWaitlistEntry.objects.select_for_update().filter(formation=formation, user=user).first()
    if not entry:
        return None
    was_offered = entry.status == FormationWaitlistEntry.Status.OFFERED
    entry.status = FormationWaitlistEntry.Status.CANCELLED
    entry.offer_expires_at = None
    entry.save(update_fields=["status", "offer_expires_at", "updated_at"])
    if was_offered:
        refresh_waitlist(formation.id)
    return entry


def waitlist_snapshot(user, formation):
    if not getattr(user, "is_authenticated", False):
        return {"status": "", "position": None, "offer_expires_at": None}
    entry = FormationWaitlistEntry.objects.filter(formation=formation, user=user).first()
    if not entry:
        return {"status": "", "position": None, "offer_expires_at": None}
    if entry.status == FormationWaitlistEntry.Status.OFFERED and entry.offer_expires_at and entry.offer_expires_at <= timezone.now():
        refresh_waitlist(formation.id)
        entry.refresh_from_db()
    position = None
    if entry.status == FormationWaitlistEntry.Status.WAITING:
        position = FormationWaitlistEntry.objects.filter(
            formation=formation,
            status=FormationWaitlistEntry.Status.WAITING,
            created_at__lt=entry.created_at,
        ).count() + 1
    return {
        "status": entry.status,
        "position": position,
        "offer_expires_at": entry.offer_expires_at,
    }


def mark_waitlist_joined(user, formation):
    now = timezone.now()
    FormationWaitlistEntry.objects.filter(formation=formation, user=user).update(
        status=FormationWaitlistEntry.Status.JOINED,
        joined_at=now,
        offer_expires_at=None,
        updated_at=now,
    )
