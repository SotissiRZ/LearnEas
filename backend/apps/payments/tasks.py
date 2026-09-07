from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .lifecycle import (
    classify_verification, mark_attempt_failed, record_event, register_provider_error, resolve_order_issues,
)
from .models import Order, PaymentEvent, PaymentIssue
from .providers import ProviderError, verify_payment


TERMINAL_FAILURES = {"CANCELLED", "CANCELED", "FAILED", "EXPIRED"}


@shared_task(name="apps.payments.tasks.reconcile_pending_payments")
def reconcile_pending_payments():
    """Répare les confirmations perdues sans doubler les effets métier."""
    min_age = max(int(getattr(settings, "PAYMENT_RECONCILIATION_MIN_AGE_SECONDS", 120)), 30)
    batch_size = min(max(int(getattr(settings, "PAYMENT_RECONCILIATION_BATCH_SIZE", 100)), 1), 500)
    cutoff = timezone.now() - timedelta(seconds=min_age)
    ids = list(
        Order.objects.filter(status=Order.Status.PENDING, created_at__lte=cutoff)
        .exclude(provider=Order.Provider.MANUAL)
        .exclude(provider_reference="")
        .order_by("created_at")
        .values_list("id", flat=True)[:batch_size]
    )

    result = {"checked": 0, "paid": 0, "failed": 0, "pending": 0, "mismatch": 0, "errors": 0}
    for order_id in ids:
        order = Order.objects.filter(pk=order_id, status=Order.Status.PENDING).first()
        if not order:
            continue
        result["checked"] += 1
        try:
            verification = verify_payment(order)
        except ProviderError as exc:
            register_provider_error(
                order, str(exc), source=PaymentEvent.Source.RECONCILIATION,
            )
            result["errors"] += 1
            continue
        except Exception as exc:
            register_provider_error(
                order, f"Réponse prestataire invalide: {exc}", source=PaymentEvent.Source.RECONCILIATION,
            )
            result["errors"] += 1
            continue

        classification = classify_verification(order, verification)
        provider_status = str(verification.get("status") or "").upper()
        terminal = set(TERMINAL_FAILURES)
        if provider_status == "REFUSED" and order.provider != Order.Provider.CINETPAY:
            terminal.add("REFUSED")

        if classification == "paid":
            try:
                from .views import CheckoutView
                with transaction.atomic():
                    locked = Order.objects.select_for_update().get(pk=order_id)
                    if locked.status != Order.Status.PENDING:
                        continue
                    CheckoutView()._fulfill(locked)
                record_event(
                    order=order, source=PaymentEvent.Source.RECONCILIATION,
                    event_type="reconciliation.paid", outcome=PaymentEvent.Outcome.ACCEPTED,
                    payload={"provider_status": provider_status, "payment_method": verification.get("payment_method")},
                )
                result["paid"] += 1
            except (Order.DoesNotExist, ValueError) as exc:
                record_event(
                    order=order, source=PaymentEvent.Source.RECONCILIATION,
                    event_type="reconciliation.fulfillment_error", outcome=PaymentEvent.Outcome.ERROR,
                    message=str(exc),
                )
                result["errors"] += 1
            continue

        if classification in {"amount_mismatch", "currency_mismatch"}:
            record_event(
                order=order, source=PaymentEvent.Source.RECONCILIATION,
                event_type="reconciliation.financial_mismatch", outcome=PaymentEvent.Outcome.REJECTED,
                payload={"classification": classification, "provider_status": provider_status},
            )
            result["mismatch"] += 1
            continue

        if provider_status in terminal:
            from .views import _release_failed_order_reservations
            with transaction.atomic():
                try:
                    locked = Order.objects.select_for_update().get(pk=order_id)
                except Order.DoesNotExist:
                    continue
                if locked.status != Order.Status.PENDING:
                    continue
                locked.status = Order.Status.FAILED
                locked.provider_status = provider_status or "FAILED"
                locked.last_provider_check_at = timezone.now()
                locked.save(update_fields=["status", "provider_status", "last_provider_check_at"])
                mark_attempt_failed(
                    locked, provider_status=provider_status or "FAILED",
                    message="État terminal confirmé pendant la réconciliation.",
                )
                _release_failed_order_reservations(locked)
                resolve_order_issues(
                    locked, (PaymentIssue.IssueType.STALE_PENDING, PaymentIssue.IssueType.PROVIDER_ERROR),
                    "Le prestataire a confirmé un état terminal.",
                )
            record_event(
                order=order, source=PaymentEvent.Source.RECONCILIATION,
                event_type="reconciliation.failed", outcome=PaymentEvent.Outcome.ACCEPTED,
                payload={"provider_status": provider_status},
            )
            result["failed"] += 1
        else:
            result["pending"] += 1

    return result


@shared_task(name="apps.payments.tasks.flag_stale_pending_payments")
def flag_stale_pending_payments():
    """Signale les commandes externes trop anciennes sans les annuler arbitrairement.

    Un wallet peut être confirmé en retard. KalanPro préfère ouvrir une anomalie et continuer
    la réconciliation plutôt que transformer localement une transaction potentiellement encaissée
    en commande échouée.
    """
    now = timezone.now()
    batch_size = min(max(int(getattr(settings, "PAYMENT_STALE_BATCH_SIZE", 200)), 1), 1000)
    ids = list(
        Order.objects.filter(
            status=Order.Status.PENDING,
            expires_at__isnull=False,
            expires_at__lte=now,
        )
        .exclude(provider=Order.Provider.MANUAL)
        .order_by("expires_at")
        .values_list("id", flat=True)[:batch_size]
    )
    created = 0
    for order in Order.objects.filter(pk__in=ids):
        _issue, was_created = PaymentIssue.objects.get_or_create(
            order=order,
            issue_type=PaymentIssue.IssueType.STALE_PENDING,
            status=PaymentIssue.Status.OPEN,
            defaults={
                "severity": PaymentIssue.Severity.WARNING,
                "message": "La commande est toujours en attente après sa fenêtre normale de confirmation.",
                "expected": {"expires_at": order.expires_at.isoformat() if order.expires_at else None},
                "observed": {"provider_status": order.provider_status, "last_provider_check_at": order.last_provider_check_at.isoformat() if order.last_provider_check_at else None},
            },
        )
        if was_created:
            created += 1
            record_event(
                order=order, source=PaymentEvent.Source.SYSTEM,
                event_type="payment.stale_pending", outcome=PaymentEvent.Outcome.RECEIVED,
                payload={"expires_at": order.expires_at.isoformat() if order.expires_at else None},
            )
    return {"checked": len(ids), "issues_created": created}


@shared_task(name="apps.payments.tasks.prepare_premium_renewals")
def prepare_premium_renewals():
    """Prépare les checkouts Premium proches de l'échéance, sans débit hors session."""
    from .models import PremiumRenewalProfile
    from .subscriptions import prepare_premium_renewal

    lead_hours = max(1, min(int(getattr(settings, "PREMIUM_RENEWAL_LEAD_HOURS", 72)), 168))
    batch_size = min(max(int(getattr(settings, "PREMIUM_RENEWAL_BATCH_SIZE", 100)), 1), 500)
    horizon = timezone.now() + timedelta(hours=lead_hours)
    ids = list(
        PremiumRenewalProfile.objects.filter(
            enabled=True,
            next_renewal_at__isnull=False,
            next_renewal_at__lte=horizon,
        )
        .order_by("next_renewal_at", "id")
        .values_list("id", flat=True)[:batch_size]
    )
    result = {"checked": 0, "prepared": 0, "reused": 0, "errors": 0}
    for profile_id in ids:
        result["checked"] += 1
        try:
            outcome = prepare_premium_renewal(profile_id)
        except Exception:
            result["errors"] += 1
            continue
        if outcome.get("prepared"):
            result["prepared"] += 1
            result["reused"] += int(bool(outcome.get("reused")))
    return result


@shared_task(name="apps.payments.tasks.settle_premium_revenue")
def settle_premium_revenue():
    """Clôture les périodes Premium échues et crédite le ledger instructeur de façon idempotente."""
    from .models import LearnerSubscription
    from .subscriptions import settle_premium_subscription

    batch_size = min(max(int(getattr(settings, "PREMIUM_SETTLEMENT_BATCH_SIZE", 200)), 1), 1000)
    ids = list(
        LearnerSubscription.all_objects.filter(
            ends_at__lte=timezone.now(),
            revenue_settled_at__isnull=True,
        )
        .order_by("ends_at", "id")
        .values_list("id", flat=True)[:batch_size]
    )
    result = {"checked": 0, "settled": 0, "allocations": 0, "errors": 0}
    for subscription_id in ids:
        result["checked"] += 1
        try:
            outcome = settle_premium_subscription(subscription_id)
        except Exception:
            result["errors"] += 1
            continue
        if outcome.get("settled"):
            result["settled"] += 1
            result["allocations"] += int(outcome.get("allocations") or 0)
    return result
