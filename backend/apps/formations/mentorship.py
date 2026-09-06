from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import Max
from django.utils import timezone

from .models import (
    FormationKind,
    FormationSession,
    FormationSessionInvite,
    FormationStatus,
    InteractiveFormation,
    MentorshipAvailabilityRule,
    MentorshipBooking,
    MentorshipOffering,
    MentorshipPass,
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
        description="Conteneur technique KalanPro pour les rendez-vous de mentorat 1:1.",
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
def create_slot(offering: MentorshipOffering, starts_at, is_active=True, availability_rule=None) -> MentorshipSlot:
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
        availability_rule=availability_rule,
    )


def expire_stale_bookings(slot=None, instructor_id=None):
    now = timezone.now()
    qs = MentorshipBooking.objects.filter(
        status=MentorshipBooking.Status.PENDING_PAYMENT,
        expires_at__isnull=False,
        expires_at__lte=now,
    ).exclude(order_items__order__status__in=["pending", "paid"])
    if slot is not None:
        qs = qs.filter(slot=slot)
    if instructor_id is not None:
        qs = qs.filter(offering__instructor_id=instructor_id)
    return qs.update(status=MentorshipBooking.Status.EXPIRED)


def _lock_mentor(instructor_id):
    # Toutes les réservations d'un même mentor passent par ce verrou. Cela évite que
    # deux requêtes concurrentes réservent deux créneaux qui se chevauchent.
    get_user_model().objects.select_for_update().get(pk=instructor_id)


def _mentor_has_overlapping_booking(offering, starts_at, *, exclude_booking_id=None):
    ends_at = starts_at + timedelta(minutes=offering.duration_minutes)
    # L'API borne une séance à 180 minutes. Une fenêtre d'un jour garde aussi une
    # marge sûre pour d'éventuelles anciennes données créées avant cette validation.
    candidates = MentorshipBooking.objects.filter(
        offering__instructor_id=offering.instructor_id,
        status__in=[MentorshipBooking.Status.PENDING_PAYMENT, MentorshipBooking.Status.CONFIRMED],
        slot__starts_at__lt=ends_at,
        slot__starts_at__gte=starts_at - timedelta(days=1),
    ).select_related("slot", "offering")
    if exclude_booking_id:
        candidates = candidates.exclude(pk=exclude_booking_id)
    for candidate in candidates:
        candidate_end = candidate.slot.starts_at + timedelta(minutes=candidate.offering.duration_minutes)
        if candidate.slot.starts_at < ends_at and candidate_end > starts_at:
            return True
    return False


@transaction.atomic
def reserve_booking(*, user, slot: MentorshipSlot, learner_note="", mentorship_pass=None) -> MentorshipBooking:
    slot = MentorshipSlot.objects.select_for_update().select_related("offering").get(pk=slot.pk)
    expire_stale_bookings(slot)
    offering = slot.offering
    _lock_mentor(offering.instructor_id)
    # Nettoie également les anciennes réservations provisoires d'autres créneaux du
    # même mentor avant de contrôler les chevauchements.
    expire_stale_bookings(instructor_id=offering.instructor_id)
    now = timezone.now()
    if not offering.published or not slot.is_active:
        raise ValueError("Ce créneau n'est plus disponible.")
    if slot.starts_at <= now + timedelta(hours=offering.booking_notice_hours):
        raise ValueError("Le délai minimum de réservation de ce créneau est dépassé.")
    if slot.bookings.filter(status__in=[MentorshipBooking.Status.PENDING_PAYMENT, MentorshipBooking.Status.CONFIRMED]).exists():
        raise ValueError("Ce créneau vient d'être réservé.")
    if _mentor_has_overlapping_booking(offering, slot.starts_at):
        raise ValueError("Le mentor possède déjà un rendez-vous sur cette plage horaire.")

    pass_obj = None
    if mentorship_pass is not None:
        pass_id = getattr(mentorship_pass, "pk", mentorship_pass)
        pass_obj = MentorshipPass.objects.select_for_update().select_related("pack").filter(pk=pass_id, user=user).first()
        if not pass_obj or pass_obj.revoked_at is not None or pass_obj.remaining_sessions <= 0:
            raise ValueError("Ce pack de mentorat n'est plus disponible.")
        if pass_obj.expires_at and pass_obj.expires_at <= now:
            raise ValueError("Ce pack de mentorat a expiré.")
        if pass_obj.expires_at and slot.starts_at > pass_obj.expires_at:
            raise ValueError("Ce créneau se situe après la date de validité de votre pack.")
        if pass_obj.pack.offering_id != offering.id:
            raise ValueError("Ce pack ne correspond pas à cette offre de mentorat.")

    booking = MentorshipBooking.objects.create(
        user=user,
        offering=offering,
        slot=slot,
        price_snapshot=0 if pass_obj else offering.price,
        expires_at=None if pass_obj or offering.price <= 0 else now + timedelta(minutes=45),
        learner_note=(learner_note or "").strip(),
        mentorship_pass=pass_obj,
    )
    if pass_obj:
        pass_obj.remaining_sessions -= 1
        pass_obj.save(update_fields=["remaining_sessions"])
        confirm_booking(booking)
        booking.refresh_from_db()
    elif offering.price <= 0:
        confirm_booking(booking)
        booking.refresh_from_db()
    return booking


@transaction.atomic
def confirm_booking(booking: MentorshipBooking) -> MentorshipBooking:
    # Ne pas joindre slot__session ici : MentorshipSlot.session est nullable et
    # PostgreSQL refuse FOR UPDATE sur le côté nullable d'un OUTER JOIN.
    # Le verrou porte sur la réservation ; session_id suffit pour les contrôles et
    # la session sera chargée normalement uniquement si nécessaire.
    booking = MentorshipBooking.objects.select_for_update().select_related(
        "user", "offering", "slot"
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


@transaction.atomic
def restore_pass_credit(booking: MentorshipBooking) -> bool:
    booking = MentorshipBooking.objects.select_for_update().get(pk=booking.pk)
    if not booking.mentorship_pass_id:
        return False
    pass_obj = MentorshipPass.objects.select_for_update().get(pk=booking.mentorship_pass_id)
    if pass_obj.revoked_at is not None:
        return False
    if pass_obj.remaining_sessions < pass_obj.total_sessions:
        pass_obj.remaining_sessions += 1
        pass_obj.save(update_fields=["remaining_sessions"])
        return True
    return False


@transaction.atomic
def reschedule_booking(*, booking: MentorshipBooking, new_slot: MentorshipSlot) -> MentorshipBooking:
    booking = MentorshipBooking.objects.select_for_update().select_related("user", "offering", "slot").get(pk=booking.pk)
    if booking.status != MentorshipBooking.Status.CONFIRMED:
        raise ValueError("Seul un rendez-vous confirmé peut être reprogrammé.")
    now = timezone.now()
    if booking.slot.starts_at <= now + timedelta(hours=booking.offering.cancellation_notice_hours):
        raise ValueError(f"La reprogrammation doit intervenir au moins {booking.offering.cancellation_notice_hours} h avant le rendez-vous.")
    new_slot = MentorshipSlot.objects.select_for_update().select_related("offering").get(pk=new_slot.pk)
    _lock_mentor(booking.offering.instructor_id)
    expire_stale_bookings(instructor_id=booking.offering.instructor_id)
    if new_slot.offering_id != booking.offering_id:
        raise ValueError("Le nouveau créneau doit appartenir à la même offre de mentorat.")
    if not new_slot.is_active or new_slot.starts_at <= now + timedelta(hours=booking.offering.booking_notice_hours):
        raise ValueError("Ce nouveau créneau n'est pas disponible.")
    if new_slot.bookings.exclude(pk=booking.pk).filter(status__in=[MentorshipBooking.Status.PENDING_PAYMENT, MentorshipBooking.Status.CONFIRMED]).exists():
        raise ValueError("Ce nouveau créneau vient d'être réservé.")
    if _mentor_has_overlapping_booking(booking.offering, new_slot.starts_at, exclude_booking_id=booking.id):
        raise ValueError("Le mentor possède déjà un rendez-vous sur cette plage horaire.")
    if booking.mentorship_pass_id:
        pass_obj = MentorshipPass.objects.select_for_update().filter(pk=booking.mentorship_pass_id).first()
        if pass_obj and pass_obj.expires_at and new_slot.starts_at > pass_obj.expires_at:
            raise ValueError("Ce nouveau créneau se situe après la date de validité du pack.")
    if not new_slot.session_id:
        raise ValueError("La salle du nouveau créneau n'est pas disponible.")

    old_session_id = booking.slot.session_id
    if old_session_id and booking.user.email:
        FormationSessionInvite.objects.filter(
            session_id=old_session_id, email__iexact=booking.user.email, revoked_at__isnull=True
        ).update(revoked_at=now)
    email = (booking.user.email or "").strip().lower()
    if not email:
        raise ValueError("Un email est requis pour accéder à la salle de mentorat.")
    FormationSessionInvite.objects.update_or_create(
        session_id=new_slot.session_id,
        email=email,
        defaults={
            "invited_by": booking.offering.instructor,
            "invited_user": booking.user,
            "accepted_at": None,
            "revoked_at": None,
        },
    )
    booking.slot = new_slot
    booking.rescheduled_at = now
    booking.reschedule_count += 1
    booking.save(update_fields=["slot", "rescheduled_at", "reschedule_count", "updated_at"])
    return booking


def generate_rule_slots(rule: MentorshipAvailabilityRule, *, horizon_days=45) -> int:
    """Synchronise les créneaux futurs générés par une règle récurrente.

    Les créneaux manuels ne sont jamais touchés. Lorsqu'une règle est modifiée ou
    désactivée, ses anciens créneaux futurs non réservés sont désactivés afin de ne
    pas laisser des disponibilités fantômes dans le catalogue. Les créneaux déjà
    réservés restent intacts pour préserver l'historique et les rendez-vous confirmés.
    """
    try:
        tz = ZoneInfo(rule.offering.timezone or "UTC")
    except (ZoneInfoNotFoundError, ValueError):
        tz = ZoneInfo("UTC")
    utc = ZoneInfo("UTC")
    now = timezone.now()
    today = timezone.localtime(now, tz).date()
    start_date = max(today, rule.valid_from)
    horizon_days = max(1, min(int(horizon_days), 120))
    end_date = start_date + timedelta(days=horizon_days)
    if rule.valid_until:
        end_date = min(end_date, rule.valid_until)

    enabled = bool(rule.is_active and rule.offering.published)
    desired_starts = set()
    if enabled and end_date >= start_date:
        current_date = start_date
        while current_date <= end_date:
            if current_date.weekday() == rule.weekday:
                local_start = datetime.combine(current_date, rule.start_time, tzinfo=tz)
                local_end = datetime.combine(current_date, rule.end_time, tzinfo=tz)
                cursor = local_start
                duration = timedelta(minutes=rule.offering.duration_minutes)
                step = timedelta(minutes=max(rule.interval_minutes, rule.offering.duration_minutes))
                while cursor + duration <= local_end:
                    starts_at = cursor.astimezone(utc)
                    if starts_at > now + timedelta(hours=rule.offering.booking_notice_hours):
                        desired_starts.add(starts_at)
                    cursor += step
            current_date += timedelta(days=1)

    # Désactive uniquement les anciens créneaux automatiques libres. Les réservations
    # PENDING/CONFIRMED restent visibles et ne sont jamais déplacées silencieusement.
    future_rule_slots = MentorshipSlot.objects.filter(
        availability_rule=rule, starts_at__gt=now
    ).prefetch_related("bookings")
    for slot in future_rule_slots:
        has_active_booking = slot.bookings.filter(
            status__in=[MentorshipBooking.Status.PENDING_PAYMENT, MentorshipBooking.Status.CONFIRMED]
        ).exists()
        should_be_active = enabled and slot.starts_at in desired_starts
        if not has_active_booking and slot.is_active != should_be_active:
            slot.is_active = should_be_active
            slot.save(update_fields=["is_active"])

    if not enabled:
        return 0

    created = 0
    for starts_at in sorted(desired_starts):
        existing = MentorshipSlot.objects.filter(offering=rule.offering, starts_at=starts_at).first()
        if existing:
            # Un créneau manuel ou généré par une autre règle garde sa provenance.
            # S'il appartient à cette règle et est libre, on peut simplement le réactiver.
            if existing.availability_rule_id == rule.id and not existing.is_active:
                if not existing.bookings.filter(
                    status__in=[MentorshipBooking.Status.PENDING_PAYMENT, MentorshipBooking.Status.CONFIRMED]
                ).exists():
                    existing.is_active = True
                    existing.save(update_fields=["is_active"])
            continue
        try:
            create_slot(rule.offering, starts_at, True, availability_rule=rule)
            created += 1
        except IntegrityError:
            # Protection complémentaire contre deux workers Celery concurrents.
            pass
    return created
