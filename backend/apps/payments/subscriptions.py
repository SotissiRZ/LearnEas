from datetime import timedelta
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
import hashlib

from django.conf import settings
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from apps.accounts.models import PlatformSettings
from apps.catalog.models import Course, PDFProduct
from apps.enrollments.models import CourseEnrollment, PDFPurchase

from .models import (
    Currency,
    InstructorLedgerEntry,
    LearnerSubscription,
    Order,
    OrderItem,
    PaymentGateway,
    PremiumContentUsage,
    PremiumRenewalProfile,
    PremiumRevenueAllocation,
)


PREMIUM_PERIOD_DAYS = 30
MONEY = Decimal("0.01")


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


def recurring_capability(provider):
    """Expose le niveau réel de récurrence du driver.

    Les drivers V92 savent préparer automatiquement un checkout avant l'échéance,
    mais aucun ne possède encore de mandat de débit hors session dans KalanPro.
    On ne prétend donc jamais avoir effectué un prélèvement automatique.
    """
    if provider in {Order.Provider.STRIPE, Order.Provider.YOUCANPAY, Order.Provider.GENIUSPAY, Order.Provider.CINETPAY}:
        return "checkout_confirmation_required"
    return "unsupported"


def premium_renewal_status(user):
    profile = PremiumRenewalProfile.objects.filter(user=user).select_related("last_order").first()
    if not profile:
        return {
            "enabled": False,
            "status": PremiumRenewalProfile.Status.PAUSED,
            "provider": None,
            "currency": None,
            "next_renewal_at": None,
            "grace_ends_at": None,
            "last_attempt_at": None,
            "failure_count": 0,
            "action_url": None,
            "recurring_mode": None,
            "automatic_charge": False,
        }
    action_url = None
    if profile.last_order_id and profile.last_order and profile.last_order.status == Order.Status.PENDING:
        action_url = profile.last_order.checkout_url or None
    return {
        "enabled": bool(profile.enabled),
        "status": profile.status,
        "provider": profile.provider,
        "currency": profile.currency,
        "next_renewal_at": profile.next_renewal_at,
        "grace_ends_at": profile.grace_ends_at,
        "last_attempt_at": profile.last_attempt_at,
        "failure_count": int(profile.failure_count),
        "action_url": action_url,
        "recurring_mode": recurring_capability(profile.provider),
        "automatic_charge": False,
    }


def premium_status(user):
    now = timezone.now()
    current = active_learner_subscription(user, now=now)
    coverage_end = premium_coverage_end(user, now=now)
    return {
        "active": bool(current),
        "starts_at": current.starts_at if current else None,
        "current_period_ends_at": current.ends_at if current else None,
        "coverage_ends_at": coverage_end,
        "renewal": premium_renewal_status(user),
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


def _sync_renewal_after_activation(order, subscription):
    profile = PremiumRenewalProfile.objects.select_for_update().filter(user=order.user).first()
    if not profile or not profile.enabled:
        return
    profile.next_renewal_at = premium_coverage_end(order.user) or subscription.ends_at
    profile.status = PremiumRenewalProfile.Status.SCHEDULED
    profile.failure_count = 0
    profile.grace_ends_at = None
    if str(order.idempotency_key or "").startswith("premium-renewal:"):
        profile.last_order = order
    profile.cancelled_at = None
    profile.save(update_fields=[
        "next_renewal_at", "status", "failure_count", "last_order", "cancelled_at", "grace_ends_at", "updated_at"
    ])


@transaction.atomic
def activate_learner_subscription(order: Order):
    if order.status != Order.Status.PAID:
        raise ValueError("La commande doit être payée avant d'activer Premium.")

    existing = LearnerSubscription.all_objects.select_for_update().filter(source_order=order).first()
    if existing:
        _sync_renewal_after_activation(order, existing)
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
    _sync_renewal_after_activation(order, subscription)
    return subscription


def reverse_premium_revenue(subscription, *, now=None):
    """Crée les écritures inverses d'une période Premium déjà répartie.

    Les allocations historiques restent présentes pour l'audit; `reversed_at` et le
    ledger signé rendent le remboursement idempotent.
    """
    now = now or timezone.now()
    reversed_count = 0
    for allocation in PremiumRevenueAllocation.objects.select_for_update().filter(
        subscription=subscription, reversed_at__isnull=True
    ).select_related("instructor"):
        InstructorLedgerEntry.objects.get_or_create(
            premium_allocation=allocation,
            entry_type=InstructorLedgerEntry.EntryType.PREMIUM_REFUND,
            defaults={
                "instructor": allocation.instructor,
                "amount": -allocation.amount,
                "reference": f"premium-refund:{allocation.id}",
                "note": f"Reprise de la part Premium · période #{subscription.id}",
            },
        )
        allocation.reversed_at = now
        allocation.save(update_fields=["reversed_at"])
        reversed_count += 1
    return reversed_count


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
    reverse_premium_revenue(subscription, now=now)
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
    profile = PremiumRenewalProfile.objects.select_for_update().filter(user=subscription.user, enabled=True).first()
    if profile:
        profile.next_renewal_at = premium_coverage_end(subscription.user)
        if profile.last_order_id == order.id:
            profile.status = PremiumRenewalProfile.Status.PAST_DUE
            profile.failure_count = min(int(profile.failure_count) + 1, 65535)
        profile.save(update_fields=["next_renewal_at", "status", "failure_count", "updated_at"])
    return True


@transaction.atomic
def record_premium_usage(user, *, course=None, pdf_product=None):
    """Enregistre au plus une ligne d'usage par contenu et par période.

    La redistribution V92 utilise des contenus distincts, pas le nombre de clics. Cela
    évite qu'un client bavard ou une mauvaise connexion gonfle artificiellement la part.
    """
    if bool(course) == bool(pdf_product):
        return None
    subscription = active_learner_subscription(user)
    if not subscription:
        return None
    target = course or pdf_product
    if not target or not getattr(target, "premium_included", False):
        return None
    defaults = {"instructor": getattr(target, "instructor", None), "interaction_count": 1}
    lookup = {"subscription": subscription, "course": course} if course else {"subscription": subscription, "pdf_product": pdf_product}
    usage, _ = PremiumContentUsage.objects.get_or_create(defaults=defaults, **lookup)
    return usage


@transaction.atomic
def settle_premium_subscription(subscription_id):
    """Répartit le pool Premium d'une période expirée entre contenus réellement utilisés.

    Chaque contenu distinct utilisé dans la période vaut une unité. Les unités d'un même
    instructeur sont regroupées, puis le reliquat d'arrondi est affecté de façon déterministe.
    """
    subscription = (
        LearnerSubscription.all_objects.select_for_update()
        .select_related("source_order")
        .filter(pk=subscription_id)
        .first()
    )
    if not subscription:
        return {"settled": False, "reason": "missing"}
    if subscription.revenue_settled_at:
        return {"settled": False, "reason": "already_settled"}
    now = timezone.now()
    if subscription.ends_at > now:
        return {"settled": False, "reason": "not_ended"}
    if subscription.revoked_at or subscription.source_order.status != Order.Status.PAID:
        subscription.creator_pool_amount = Decimal("0")
        subscription.platform_revenue_amount = Decimal("0")
        subscription.revenue_settled_at = now
        subscription.save(update_fields=["creator_pool_amount", "platform_revenue_amount", "revenue_settled_at", "updated_at"])
        return {"settled": True, "allocations": 0, "creator_pool": "0.00", "reason": "revoked_or_unpaid"}

    config = PlatformSettings.load()
    pool_percent = Decimal(str(config.learner_premium_creator_pool_percent))
    gross = Decimal(subscription.source_order.base_total_amount or 0).quantize(MONEY, rounding=ROUND_HALF_UP)
    pool = (gross * pool_percent / Decimal("100")).quantize(MONEY, rounding=ROUND_HALF_UP)
    # Le poids réel est le nombre de contenus distincts par instructeur.
    weights = {}
    for usage in subscription.content_usage.filter(instructor__isnull=False).values("instructor_id"):
        weights[usage["instructor_id"]] = weights.get(usage["instructor_id"], 0) + 1

    if pool <= 0 or not weights:
        subscription.creator_pool_amount = Decimal("0")
        subscription.platform_revenue_amount = gross
        subscription.revenue_settled_at = now
        subscription.save(update_fields=["creator_pool_amount", "platform_revenue_amount", "revenue_settled_at", "updated_at"])
        return {"settled": True, "allocations": 0, "creator_pool": "0.00", "platform_revenue": str(gross)}

    total_weight = sum(weights.values())
    raw_allocations = []
    allocated = Decimal("0")
    instructor_ids = sorted(weights)
    for instructor_id in instructor_ids:
        raw = pool * Decimal(weights[instructor_id]) / Decimal(total_weight)
        amount = raw.quantize(MONEY, rounding=ROUND_DOWN)
        raw_allocations.append([instructor_id, amount, Decimal(weights[instructor_id])])
        allocated += amount
    residual = pool - allocated
    if residual > 0:
        # Plus gros poids, puis plus petit id pour être déterministe.
        winner = sorted(raw_allocations, key=lambda row: (-row[2], row[0]))[0]
        winner[1] += residual

    created = 0
    actual_pool = Decimal("0")
    for instructor_id, amount, weight in raw_allocations:
        if amount <= 0:
            continue
        allocation, was_created = PremiumRevenueAllocation.objects.get_or_create(
            subscription=subscription,
            instructor_id=instructor_id,
            defaults={"amount": amount, "usage_weight": weight, "creator_pool_amount": pool},
        )
        InstructorLedgerEntry.objects.get_or_create(
            premium_allocation=allocation,
            entry_type=InstructorLedgerEntry.EntryType.PREMIUM,
            defaults={
                "instructor_id": instructor_id,
                "amount": allocation.amount,
                "reference": f"premium:{allocation.id}",
                "note": f"Part KalanPro Premium · période #{subscription.id}",
            },
        )
        actual_pool += allocation.amount
        created += int(was_created)

    subscription.creator_pool_amount = actual_pool
    subscription.platform_revenue_amount = gross - actual_pool
    subscription.revenue_settled_at = now
    subscription.save(update_fields=["creator_pool_amount", "platform_revenue_amount", "revenue_settled_at", "updated_at"])
    return {
        "settled": True,
        "allocations": len(raw_allocations),
        "created": created,
        "creator_pool": str(actual_pool),
        "platform_revenue": str(subscription.platform_revenue_amount),
    }


@transaction.atomic
def configure_premium_renewal(user, *, enabled, provider=None, currency=None):
    if getattr(user, "role", None) != "student":
        raise PermissionError("Le renouvellement Premium est réservé aux comptes apprenants.")
    coverage_end = premium_coverage_end(user)
    profile, _ = PremiumRenewalProfile.objects.select_for_update().get_or_create(user=user)
    if not enabled:
        profile.enabled = False
        profile.status = PremiumRenewalProfile.Status.CANCELLED
        profile.cancelled_at = timezone.now()
        profile.next_renewal_at = coverage_end
        profile.grace_ends_at = None
        profile.save(update_fields=["enabled", "status", "cancelled_at", "next_renewal_at", "grace_ends_at", "updated_at"])
        return profile
    if not coverage_end:
        raise ValueError("Activez d'abord KalanPro Premium avant son renouvellement automatique.")

    latest = (
        LearnerSubscription.all_objects.filter(user=user, revoked_at__isnull=True)
        .select_related("source_order")
        .order_by("-ends_at", "-id")
        .first()
    )
    selected_provider = str(provider or (latest.source_order.provider if latest else "") or profile.provider).strip().lower()
    selected_currency = str(currency or (latest.source_order.currency if latest else "") or profile.currency or "EUR").strip().upper()
    if selected_provider == Order.Provider.MANUAL or recurring_capability(selected_provider) == "unsupported":
        raise ValueError("Choisissez un moyen de paiement en ligne pour préparer les renouvellements Premium.")
    gateway = PaymentGateway.objects.filter(code=selected_provider, is_active=True).first()
    if not gateway:
        raise ValueError("Le moyen de paiement choisi n'est pas actif.")
    curr = Currency.objects.filter(code=selected_currency, is_active=True).first()
    if not curr:
        raise ValueError("La devise choisie n'est pas active.")
    if gateway.supported_currencies and selected_currency not in gateway.supported_currencies:
        raise ValueError(f"{gateway.name} ne prend pas en charge {selected_currency}.")
    from .providers import is_configured
    if selected_provider != Order.Provider.MANUAL and not is_configured(selected_provider, sandbox=gateway.sandbox):
        raise ValueError("Le moyen de paiement choisi n'est pas configuré côté serveur.")

    profile.enabled = True
    profile.status = PremiumRenewalProfile.Status.SCHEDULED
    profile.provider = selected_provider
    profile.currency = selected_currency
    profile.next_renewal_at = coverage_end
    profile.grace_ends_at = None
    profile.cancelled_at = None
    profile.save(update_fields=["enabled", "status", "provider", "currency", "next_renewal_at", "grace_ends_at", "cancelled_at", "updated_at"])
    return profile


@transaction.atomic
def prepare_premium_renewal(profile_id):
    """Prépare un checkout de renouvellement idempotent avant l'échéance.

    V92 n'enregistre aucun numéro de carte ni token wallet. Avec les drivers actuels,
    l'apprenant doit donc confirmer le checkout hébergé; le renouvellement est orchestré
    automatiquement, pas débité silencieusement.
    """
    from .lifecycle import current_attempt, mark_attempt_redirected, record_event
    from .models import PaymentAttempt, PaymentEvent
    from .providers import ProviderError, create_checkout, is_configured, normalize_provider_amount

    profile = PremiumRenewalProfile.objects.select_for_update().select_related("user", "last_order").filter(pk=profile_id).first()
    if not profile or not profile.enabled:
        return {"prepared": False, "reason": "disabled"}
    coverage_end = premium_coverage_end(profile.user)
    now = timezone.now()
    lead_hours = max(1, min(int(getattr(settings, "PREMIUM_RENEWAL_LEAD_HOURS", 72)), 168))
    grace_hours = max(1, min(int(getattr(settings, "PREMIUM_RENEWAL_GRACE_HOURS", 48)), 168))
    cycle_anchor = coverage_end or profile.next_renewal_at
    if coverage_end:
        profile.grace_ends_at = coverage_end + timedelta(hours=grace_hours)
        if coverage_end > now + timedelta(hours=lead_hours):
            profile.next_renewal_at = coverage_end
            profile.status = PremiumRenewalProfile.Status.SCHEDULED
            profile.save(update_fields=["next_renewal_at", "grace_ends_at", "status", "updated_at"])
            return {"prepared": False, "reason": "not_due"}
    else:
        grace_end = profile.grace_ends_at or (cycle_anchor + timedelta(hours=grace_hours) if cycle_anchor else None)
        if not cycle_anchor or not grace_end or now > grace_end:
            profile.status = PremiumRenewalProfile.Status.PAUSED
            profile.next_renewal_at = None
            profile.grace_ends_at = None
            profile.save(update_fields=["status", "next_renewal_at", "grace_ends_at", "updated_at"])
            return {"prepared": False, "reason": "grace_expired"}
        profile.status = PremiumRenewalProfile.Status.PAST_DUE
        profile.grace_ends_at = grace_end
        profile.save(update_fields=["status", "grace_ends_at", "updated_at"])

    if profile.last_order_id and profile.last_order and profile.last_order.status == Order.Status.PENDING and profile.last_order.checkout_url:
        if not profile.last_order.expires_at or profile.last_order.expires_at > now:
            profile.status = PremiumRenewalProfile.Status.ACTION_REQUIRED
            profile.last_attempt_at = now
            profile.save(update_fields=["status", "last_attempt_at", "updated_at"])
            return {"prepared": True, "reused": True, "order_id": profile.last_order_id, "checkout_url": profile.last_order.checkout_url}
        profile.last_order.status = Order.Status.FAILED
        profile.last_order.provider_status = profile.last_order.provider_status or "EXPIRED"
        profile.last_order.save(update_fields=["status", "provider_status"])
        profile.failure_count = min(int(profile.failure_count) + 1, 65535)
    if profile.last_order_id and profile.last_order and profile.last_order.status == Order.Status.PAID:
        profile.status = PremiumRenewalProfile.Status.SCHEDULED

    gateway = PaymentGateway.objects.filter(code=profile.provider, is_active=True).first()
    currency = Currency.objects.filter(code=profile.currency, is_active=True).first()
    if not gateway or not currency or profile.provider == Order.Provider.MANUAL:
        profile.status = PremiumRenewalProfile.Status.ACTION_REQUIRED
        profile.failure_count = min(int(profile.failure_count) + 1, 65535)
        profile.last_attempt_at = now
        profile.save(update_fields=["status", "failure_count", "last_attempt_at", "updated_at"])
        return {"prepared": False, "reason": "gateway_unavailable"}
    if gateway.supported_currencies and currency.code not in gateway.supported_currencies:
        return {"prepared": False, "reason": "currency_unsupported"}
    if not is_configured(profile.provider, sandbox=gateway.sandbox):
        return {"prepared": False, "reason": "provider_not_configured"}

    config = PlatformSettings.load()
    if not config.learner_premium_enabled:
        return {"prepared": False, "reason": "premium_disabled"}
    base_total = Decimal(config.learner_premium_monthly_eur)
    quantum = Decimal("1").scaleb(-int(currency.decimal_places))
    total = (base_total * Decimal(currency.exchange_rate)).quantize(quantum, rounding=ROUND_HALF_UP)
    total = normalize_provider_amount(profile.provider, total, currency.code)
    cycle_key = cycle_anchor.strftime("%Y%m%d%H%M")
    idempotency_key = f"premium-renewal:{profile.id}:{cycle_key}:a{int(profile.failure_count)}"
    fingerprint = hashlib.sha256(f"premium|{profile.user_id}|{base_total}|{currency.code}|{cycle_key}".encode()).hexdigest()
    expiry_hours = min(max(int(getattr(settings, "PAYMENT_ORDER_EXPIRY_HOURS", 24)), 1), 168)
    order, created = Order.objects.get_or_create(
        user=profile.user,
        idempotency_key=idempotency_key,
        defaults={
            "provider": profile.provider,
            "provider_sandbox": bool(gateway.sandbox),
            "base_total_amount": base_total,
            "total_amount": total,
            "currency": currency.code,
            "request_fingerprint": fingerprint,
            "expires_at": now + timedelta(hours=expiry_hours),
        },
    )
    if created or not order.checkout_url:
        OrderItem.objects.get_or_create(
            order=order,
            item_type=OrderItem.ItemType.LEARNER_SUBSCRIPTION,
            entitlement_code="premium",
            defaults={
                "unit_price": base_total,
                "platform_fee_amount": base_total,
                "instructor_earning_amount": Decimal("0"),
            },
        )
        attempt = current_attempt(order)
        try:
            checkout_url, reference = create_checkout(order, profile.user)
        except ProviderError as exc:
            attempt.status = PaymentAttempt.Status.ERROR
            attempt.last_error = str(exc)[:500]
            attempt.save(update_fields=["status", "last_error", "updated_at"])
            profile.status = PremiumRenewalProfile.Status.ACTION_REQUIRED
            profile.failure_count = min(int(profile.failure_count) + 1, 65535)
            profile.last_attempt_at = now
            profile.last_order = order
            profile.save(update_fields=["status", "failure_count", "last_attempt_at", "last_order", "updated_at"])
            return {"prepared": False, "reason": "provider_error", "detail": str(exc)}
        order.checkout_url = checkout_url
        order.provider_reference = str(reference or "")[:255]
        order.provider_status = "PENDING"
        order.save(update_fields=["checkout_url", "provider_reference", "provider_status"])
        mark_attempt_redirected(order, provider_reference=order.provider_reference)
        record_event(
            order=order,
            source=PaymentEvent.Source.SYSTEM,
            event_type="premium.renewal_checkout_prepared",
            outcome=PaymentEvent.Outcome.ACCEPTED,
            payload={"coverage_end": cycle_anchor.isoformat(), "provider": profile.provider, "currency": currency.code},
        )

    profile.last_order = order
    profile.last_attempt_at = now
    profile.status = PremiumRenewalProfile.Status.ACTION_REQUIRED
    profile.next_renewal_at = cycle_anchor
    profile.save(update_fields=["last_order", "last_attempt_at", "status", "next_renewal_at", "grace_ends_at", "updated_at"])
    try:
        from apps.notifications.models import InAppNotification
        from apps.notifications.services import queue_in_app_event
        queue_in_app_event(
            user=profile.user,
            event_key=f"inapp:premium-renewal:{order.id}",
            category=InAppNotification.Category.PAYMENT,
            event_type="premium_renewal",
            title="Renouvellement KalanPro Premium à confirmer",
            body=(
                "Votre abonnement a expiré, mais le paiement peut encore être confirmé pendant la fenêtre de rattrapage."
                if coverage_end is None
                else "Votre renouvellement a été préparé. Confirmez le paiement avant l'échéance pour éviter une interruption."
            ),
            action_url=order.checkout_url or "/dashboard/student",
            metadata={"order_id": order.id, "coverage_end": cycle_anchor.isoformat(), "grace_ends_at": profile.grace_ends_at.isoformat() if profile.grace_ends_at else None},
            priority=InAppNotification.Priority.HIGH,
        )
    except Exception:
        pass
    return {"prepared": True, "reused": not created, "order_id": order.id, "checkout_url": order.checkout_url}


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
    record_premium_usage(user, course=course)
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
    record_premium_usage(user, pdf_product=pdf)
    return purchase, created
