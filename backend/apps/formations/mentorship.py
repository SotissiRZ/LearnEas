from datetime import timedelta
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from .models import (
    FormationKind,
    FormationSession,
    FormationSessionInvite,
    FormationStatus,
    InteractiveFormation,
    MentorshipBooking,
    MentorshipOffering,
    MentorshipSlot,
)


def ensure_room_formation(offering: MentorshipOffering) -> InteractiveFormation:
    """Crée un conteneur live privé réutilisé par tous les créneaux d'une offre.

    Le conteneur n'est jamais publié dans le catalogue. Chaque réservation confirmée
    reçoit uniquement une invitation à sa séance, donc un apprenant ne peut pas ouvrir
    les autres créneaux du mentor.
    """
    if offering.room_formation_id:
        return offering.room_formation
    room = InteractiveFormation.objects.create(
        instructor=offering.instructor,
        title=f"Mentorat privé · {offering.title}",
        description="Conteneur technique LearnEas pour les rendez-vous de mentorat 1:1.",
        kind=FormationKind.MENTORSHIP,
        level="beginner",
        language=offering.language,
        price=0,
        num_sessions=1,
        session_duration_minutes=offering.duration_minutes,
        max_students=1,
        status=FormationStatus.SCHEDULED,
        published=False,
        cohort_name="",
        cohort_timezone=offering.timezone,
        min_students=1,
        certificate_enabled=False,
        certificate_auto_issue=False,
    )
    offering.room_formation = room
    offering.save(update_fields=["room_formation"])
    return room


@transaction.atomic
def create_slot(offering: MentorshipOffering, starts_at, is_active=True) -> MentorshipSlot:
    offering = MentorshipOffering.objects.select_for_update().get(pk=offering.pk)
    room = ensure_room_formation(offering)
    next_number = (room.sessions.aggregate(v=Max("session_number"))["v"] or 0) + 1
    room_updates = []
    if room.num_sessions < next_number:
        room.num_sessions = next_number
        room_updates.append("num_sessions")
    if room.session_duration_minutes != offering.duration_minutes:
        room.session_duration_minutes = offering.duration_minutes
        room_updates.append("session_duration_minutes")
    if room.status in {FormationStatus.COMPLETED, FormationStatus.CANCELLED}:
        room.status = FormationStatus.SCHEDULED
        room_updates.append("status")
    if room_updates:
        room.save(update_fields=room_updates)
    session = FormationSession.objects.create(
        formation=room,
        session_number=next_number,
        scheduled_at=starts_at,
        duration_minutes=offering.duration_minutes,
        meeting_link="",
    )
    return MentorshipSlot.objects.create(
        offering=offering,
        starts_at=starts_at,
        is_active=is_active,
        session=session,
    )


def expire_stale_bookings(slot=None):
    now = timezone.now()
    qs = MentorshipBooking.objects.filter(
        status=MentorshipBooking.Status.PENDING_PAYMENT,
        expires_at__isnull=False,
        expires_at__lte=now,
    ).exclude(order_items__order__status__in=["pending", "paid"])
    if slot is not None:
        qs = qs.filter(slot=slot)
    return qs.update(status=MentorshipBooking.Status.EXPIRED)


@transaction.atomic
def reserve_booking(*, user, slot: MentorshipSlot, learner_note="") -> MentorshipBooking:
    slot = MentorshipSlot.objects.select_for_update().select_related("offering").get(pk=slot.pk)
    expire_stale_bookings(slot)
    offering = slot.offering
    now = timezone.now()
    if not offering.published or not slot.is_active:
        raise ValueError("Ce créneau n'est plus disponible.")
    if slot.starts_at <= now + timedelta(hours=offering.booking_notice_hours):
        raise ValueError("Le délai minimum de réservation de ce créneau est dépassé.")
    if slot.bookings.filter(status__in=[MentorshipBooking.Status.PENDING_PAYMENT, MentorshipBooking.Status.CONFIRMED]).exists():
        raise ValueError("Ce créneau vient d'être réservé.")
    booking = MentorshipBooking.objects.create(
        user=user,
        offering=offering,
        slot=slot,
        price_snapshot=offering.price,
        expires_at=now + timedelta(minutes=45) if offering.price > 0 else None,
        learner_note=(learner_note or "").strip(),
    )
    if offering.price <= 0:
        confirm_booking(booking)
        booking.refresh_from_db()
    return booking


@transaction.atomic
def confirm_booking(booking: MentorshipBooking) -> MentorshipBooking:
    booking = MentorshipBooking.objects.select_for_update().select_related(
        "user", "offering", "slot", "slot__session"
    ).get(pk=booking.pk)
    if booking.status == MentorshipBooking.Status.CONFIRMED:
        return booking
    if booking.status != MentorshipBooking.Status.PENDING_PAYMENT:
        raise ValueError("Cette réservation ne peut plus être confirmée.")
    if booking.expires_at and booking.expires_at <= timezone.now():
        # Un prestataire peut confirmer le paiement après la fin du délai d'affichage local.
        # Si la commande liée est déjà PAID, le paiement doit rester la source de vérité et
        # la réservation est finalisée au lieu d'être perdue après encaissement.
        paid_order_exists = booking.order_items.filter(order__status="paid").exists()
        if not paid_order_exists:
            booking.status = MentorshipBooking.Status.EXPIRED
            booking.save(update_fields=["status", "updated_at"])
            raise ValueError("La réservation a expiré. Choisissez un nouveau créneau.")
    if not booking.slot.session_id:
        raise ValueError("La salle de mentorat n'est pas disponible.")
    email = (booking.user.email or "").strip().lower()
    if not email:
        raise ValueError("Un email est requis pour accéder à la salle de mentorat.")
    FormationSessionInvite.objects.update_or_create(
        session=booking.slot.session,
        email=email,
        defaults={
            "invited_by": booking.offering.instructor,
            "invited_user": booking.user,
            "accepted_at": None,
            "revoked_at": None,
        },
    )
    booking.status = MentorshipBooking.Status.CONFIRMED
    booking.confirmed_at = timezone.now()
    booking.expires_at = None
    booking.save(update_fields=["status", "confirmed_at", "expires_at", "updated_at"])
    return booking
