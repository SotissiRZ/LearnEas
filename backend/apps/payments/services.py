from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.enrollments.models import Certificate, CertificateEvent, CourseEnrollment, PDFPurchase
from apps.formations.models import FormationEnrollment, FormationSessionInvite, MentorshipBooking

from .models import FormationSeatReservation, InstructorLedgerEntry, Order, OrderItem


def _revoke_certificates_for_enrollment(*, course_enrollment=None, formation_enrollment=None, actor=None, reason: str):
    qs = Certificate.objects.select_for_update().filter(status=Certificate.Status.ACTIVE)
    if course_enrollment is not None:
        qs = qs.filter(course_enrollment=course_enrollment)
    elif formation_enrollment is not None:
        qs = qs.filter(formation_enrollment=formation_enrollment)
    else:
        return 0
    now = timezone.now()
    count = 0
    for cert in qs:
        cert.status = Certificate.Status.REVOKED
        cert.revoked_at = now
        cert.revocation_reason = reason
        cert.save(update_fields=["status", "revoked_at", "revocation_reason"])
        CertificateEvent.objects.create(
            certificate=cert,
            event_type=CertificateEvent.EventType.REVOKED,
            actor=actor,
            details={"reason": reason, "automatic": True, "source": "order_refund"},
        )
        count += 1
    return count


def record_sale_ledger(order: Order):
    """Crée une écriture de vente par ligne, de façon idempotente."""
    for item in order.items.select_related("instructor").all():
        if not item.instructor_id or Decimal(item.instructor_earning_amount) == 0:
            continue
        InstructorLedgerEntry.objects.get_or_create(
            order_item=item,
            entry_type=InstructorLedgerEntry.EntryType.SALE,
            defaults={
                "instructor_id": item.instructor_id,
                "amount": item.instructor_earning_amount,
                "reference": order.invoice_number,
                "note": "Vente confirmée",
            },
        )


def record_refund_ledger(order: Order):
    """Contre-passe les ventes d'une commande remboursée, sans supprimer l'historique."""
    for item in order.items.select_related("instructor").all():
        if not item.instructor_id or Decimal(item.instructor_earning_amount) == 0:
            continue
        InstructorLedgerEntry.objects.get_or_create(
            order_item=item,
            entry_type=InstructorLedgerEntry.EntryType.REFUND,
            defaults={
                "instructor_id": item.instructor_id,
                "amount": -Decimal(item.instructor_earning_amount),
                "reference": order.refund_reference or order.invoice_number,
                "note": order.refund_reason or "Commande remboursée",
            },
        )


def record_payout_ledger(payout):
    if Decimal(payout.amount) == 0:
        return
    InstructorLedgerEntry.objects.get_or_create(
        payout=payout,
        entry_type=InstructorLedgerEntry.EntryType.PAYOUT,
        defaults={
            "instructor_id": payout.instructor_id,
            "amount": -Decimal(payout.amount),
            "reference": payout.reference,
            "note": payout.note or "Versement instructeur",
        },
    )


@transaction.atomic
def revoke_order_entitlements(order: Order, *, actor=None, reason: str = "Commande remboursée") -> dict:
    """Révoque uniquement les droits effectivement issus de cette commande.

    Les lignes restent en base pour préserver progression, présence et preuves de certificat.
    Le manager `objects` masque ces droits aux contrôles d'accès; `all_objects` conserve l'audit.
    """
    order = Order.objects.select_for_update().get(pk=order.pk)
    now = timezone.now()
    revoked = {"courses": 0, "pdfs": 0, "formations": 0, "mentorships": 0, "certificates": 0, "employer_entitlements": 0}

    for item in order.items.select_related(
        "course", "pdf_product", "formation", "mentorship_booking__slot__session"
    ).all():
        if item.course_id:
            enrollment = CourseEnrollment.all_objects.select_for_update().filter(
                user=order.user, course_id=item.course_id, source_order=order, revoked_at__isnull=True
            ).first()
            if enrollment:
                revoked["certificates"] += _revoke_certificates_for_enrollment(
                    course_enrollment=enrollment, actor=actor, reason=reason
                )
                enrollment.revoked_at = now
                enrollment.revocation_reason = reason
                enrollment.save(update_fields=["revoked_at", "revocation_reason"])
                item.course.students_count = item.course.enrollments.count()
                item.course.save(update_fields=["students_count"])
                revoked["courses"] += 1

        if item.pdf_product_id:
            purchase = PDFPurchase.all_objects.select_for_update().filter(
                user=order.user, pdf_product_id=item.pdf_product_id, source_order=order, revoked_at__isnull=True
            ).first()
            if purchase:
                purchase.revoked_at = now
                purchase.revocation_reason = reason
                purchase.save(update_fields=["revoked_at", "revocation_reason"])
                revoked["pdfs"] += 1

        if item.formation_id:
            enrollment = FormationEnrollment.all_objects.select_for_update().filter(
                user=order.user, formation_id=item.formation_id, source_order=order, revoked_at__isnull=True
            ).first()
            if enrollment:
                revoked["certificates"] += _revoke_certificates_for_enrollment(
                    formation_enrollment=enrollment, actor=actor, reason=reason
                )
                enrollment.revoked_at = now
                enrollment.revocation_reason = reason
                enrollment.save(update_fields=["revoked_at", "revocation_reason"])
                revoked["formations"] += 1

        if item.mentorship_booking_id:
            booking = MentorshipBooking.objects.select_for_update().select_related("slot__session").filter(
                pk=item.mentorship_booking_id,
                status=MentorshipBooking.Status.CONFIRMED,
            ).first()
            if booking:
                booking.status = MentorshipBooking.Status.CANCELLED
                booking.cancelled_at = now
                booking.save(update_fields=["status", "cancelled_at", "updated_at"])
                if booking.slot.session_id:
                    FormationSessionInvite.objects.filter(
                        session_id=booking.slot.session_id,
                        invited_user=booking.user,
                        revoked_at__isnull=True,
                    ).update(revoked_at=now)
                revoked["mentorships"] += 1

    if order.items.filter(item_type=OrderItem.ItemType.EMPLOYER).exists():
        from apps.opportunities.services import revoke_employer_entitlement
        if revoke_employer_entitlement(order, reason=reason):
            revoked["employer_entitlements"] = 1

    FormationSeatReservation.objects.filter(order=order).delete()
    record_refund_ledger(order)
    return revoked
