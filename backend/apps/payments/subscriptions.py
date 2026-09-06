from datetime import timedelta

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from apps.catalog.models import Course, PDFProduct
from apps.enrollments.models import CourseEnrollment, PDFPurchase

from .models import LearnerSubscription, Order


PREMIUM_PERIOD_DAYS = 30


def premium_coverage_end(user, *, now=None):
    """Retourne la fin de couverture continue à partir de maintenant.

    Les renouvellements peuvent être achetés avant l'échéance. Ils sont chaînés et
    prolongent donc la même fenêtre d'accès sans donner deux abonnements simultanés.
    """
    now = now or timezone.now()
    periods = list(
        LearnerSubscription.all_objects.filter(
            user=user,
            revoked_at__isnull=True,
            ends_at__gt=now,
        ).order_by("starts_at", "id").values_list("starts_at", "ends_at")
    )
    cursor = None
    for starts_at, ends_at in periods:
        if cursor is None:
            if starts_at > now:
                break
            cursor = ends_at
            continue
        if starts_at > cursor:
            break
        if ends_at > cursor:
            cursor = ends_at
    return cursor


def active_learner_subscription(user, *, now=None):
    now = now or timezone.now()
    return (
        LearnerSubscription.all_objects.filter(
            user=user,
            revoked_at__isnull=True,
            starts_at__lte=now,
            ends_at__gt=now,
        )
        .order_by("-ends_at", "-id")
        .first()
    )


def premium_status(user):
    now = timezone.now()
    current = active_learner_subscription(user, now=now)
    coverage_end = premium_coverage_end(user, now=now)
    return {
        "active": bool(current),
        "starts_at": current.starts_at if current else None,
        "current_period_ends_at": current.ends_at if current else None,
        "coverage_ends_at": coverage_end,
    }


def _refresh_subscription_entitlements(user):
    """Aligne les droits temporaires sur la couverture restante du pass.

    Après un remboursement d'une période antérieure, le pointeur d'audit est
    également recalé sur la période actuellement active. Un achat à l'unité
    reste exclu grâce à `source_order__isnull=True`.
    """
    now = timezone.now()
    coverage_end = premium_coverage_end(user, now=now)
    current = active_learner_subscription(user, now=now)
    expiry = coverage_end or now
    update = {"access_expires_at": expiry}
    if current:
        update["source_subscription"] = current
    CourseEnrollment.all_objects.filter(
        user=user,
        source_subscription__isnull=False,
        source_order__isnull=True,
        revoked_at__isnull=True,
    ).update(**update)
    PDFPurchase.all_objects.filter(
        user=user,
        source_subscription__isnull=False,
        source_order__isnull=True,
        revoked_at__isnull=True,
    ).update(**update)


@transaction.atomic
def activate_learner_subscription(order: Order):
    if order.status != Order.Status.PAID:
        raise ValueError("La commande doit être payée avant d'activer Premium.")

    existing = LearnerSubscription.all_objects.select_for_update().filter(source_order=order).first()
    if existing:
        return existing

    now = timezone.now()
    latest_end = (
        LearnerSubscription.all_objects.select_for_update()
        .filter(user=order.user, revoked_at__isnull=True, ends_at__gt=now)
        .aggregate(v=Max("ends_at"))["v"]
    )
    starts_at = max(now, latest_end) if latest_end else now
    subscription = LearnerSubscription.all_objects.create(
        user=order.user,
        source_order=order,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(days=PREMIUM_PERIOD_DAYS),
    )
    _refresh_subscription_entitlements(order.user)
    return subscription


@transaction.atomic
def revoke_learner_subscription(order: Order, *, reason="Commande remboursée"):
    subscription = (
        LearnerSubscription.all_objects.select_for_update()
        .filter(source_order=order, revoked_at__isnull=True)
        .first()
    )
    if not subscription:
        return False

    now = timezone.now()
    duration = subscription.ends_at - subscription.starts_at
    old_end = subscription.ends_at
    subscription.revoked_at = now
    subscription.revocation_reason = str(reason or "Commande remboursée")[:500]
    subscription.save(update_fields=["revoked_at", "revocation_reason", "updated_at"])

    # Les périodes achetées après celle-ci avancent pour ne pas laisser un trou artificiel.
    future = list(
        LearnerSubscription.all_objects.select_for_update()
        .filter(
            user=subscription.user,
            revoked_at__isnull=True,
            starts_at__gte=old_end,
        )
        .order_by("starts_at", "id")
    )
    for period in future:
        period.starts_at -= duration
        period.ends_at -= duration
        period.save(update_fields=["starts_at", "ends_at", "updated_at"])

    _refresh_subscription_entitlements(subscription.user)
    return True


@transaction.atomic
def claim_premium_course(user, course_id):
    subscription = active_learner_subscription(user)
    coverage_end = premium_coverage_end(user)
    if not subscription or not coverage_end:
        raise PermissionError("Aucun abonnement KalanPro Premium actif.")
    course = Course.objects.filter(pk=course_id, published=True, premium_included=True).first()
    if not course:
        raise LookupError("Cours Premium introuvable ou indisponible.")

    enrollment = CourseEnrollment.all_objects.select_for_update().filter(user=user, course=course).first()
    if enrollment and enrollment.access_expires_at is None and enrollment.source_subscription_id is None:
        return enrollment, False
    if enrollment is None:
        enrollment = CourseEnrollment.all_objects.create(
            user=user,
            course=course,
            source_subscription=subscription,
            access_expires_at=coverage_end,
        )
        created = True
    else:
        enrollment.revoked_at = None
        enrollment.revocation_reason = ""
        enrollment.source_order = None
        enrollment.source_subscription = subscription
        enrollment.access_expires_at = coverage_end
        enrollment.save(update_fields=[
            "revoked_at", "revocation_reason", "source_order", "source_subscription", "access_expires_at"
        ])
        created = False
    course.students_count = course.enrollments.count()
    course.save(update_fields=["students_count"])
    return enrollment, created


@transaction.atomic
def claim_premium_pdf(user, pdf_id):
    subscription = active_learner_subscription(user)
    coverage_end = premium_coverage_end(user)
    if not subscription or not coverage_end:
        raise PermissionError("Aucun abonnement KalanPro Premium actif.")
    pdf = PDFProduct.objects.filter(pk=pdf_id, published=True, premium_included=True).first()
    if not pdf:
        raise LookupError("PDF Premium introuvable ou indisponible.")

    purchase = PDFPurchase.all_objects.select_for_update().filter(user=user, pdf_product=pdf).first()
    if purchase and purchase.access_expires_at is None and purchase.source_subscription_id is None:
        return purchase, False
    if purchase is None:
        purchase = PDFPurchase.all_objects.create(
            user=user,
            pdf_product=pdf,
            source_subscription=subscription,
            access_expires_at=coverage_end,
        )
        pdf.downloads_count += 1
        pdf.save(update_fields=["downloads_count"])
        created = True
    else:
        was_inactive = bool(purchase.revoked_at or (purchase.access_expires_at and purchase.access_expires_at <= timezone.now()))
        purchase.revoked_at = None
        purchase.revocation_reason = ""
        purchase.source_order = None
        purchase.source_subscription = subscription
        purchase.access_expires_at = coverage_end
        purchase.save(update_fields=[
            "revoked_at", "revocation_reason", "source_order", "source_subscription", "access_expires_at"
        ])
        if was_inactive:
            pdf.downloads_count += 1
            pdf.save(update_fields=["downloads_count"])
        created = False
    return purchase, created
