from decimal import Decimal
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import Order
from .providers import ProviderError, verify_payment


TERMINAL_FAILURES = {"CANCELLED", "CANCELED", "FAILED"}


@shared_task(name="apps.payments.tasks.reconcile_pending_payments")
def reconcile_pending_payments():
    """Répare les confirmations de paiement perdues sans doubler les effets métier.

    L'appel réseau est fait hors verrou DB. La commande est reverrouillée juste avant toute
    transition ; `_fulfill` reste l'unique chemin d'attribution des droits/ledger.
    """
    min_age = max(int(getattr(settings, "PAYMENT_RECONCILIATION_MIN_AGE_SECONDS", 120)), 30)
    batch_size = min(max(int(getattr(settings, "PAYMENT_RECONCILIATION_BATCH_SIZE", 100)), 1), 500)
    cutoff = timezone.now() - timedelta(seconds=min_age)
    ids = list(
        Order.objects.filter(
            status=Order.Status.PENDING,
            created_at__lte=cutoff,
        )
        .exclude(provider=Order.Provider.MANUAL)
        .exclude(provider_reference="")
        .order_by("created_at")
        .values_list("id", flat=True)[:batch_size]
    )

    result = {"checked": 0, "paid": 0, "failed": 0, "pending": 0, "errors": 0}
    for order_id in ids:
        order = Order.objects.filter(pk=order_id, status=Order.Status.PENDING).first()
        if not order:
            continue
        result["checked"] += 1
        try:
            verification = verify_payment(order)
        except ProviderError:
            result["errors"] += 1
            continue
        except Exception:
            # La tâche de réconciliation ne doit jamais interrompre tout le batch à cause
            # d'un prestataire ou d'une réponse malformée.
            result["errors"] += 1
            continue

        provider_status = str(verification.get("status") or "").upper()
        terminal = set(TERMINAL_FAILURES)
        if provider_status == "REFUSED" and order.provider != Order.Provider.CINETPAY:
            terminal.add("REFUSED")

        if verification.get("paid"):
            try:
                amount = Decimal(str(verification.get("amount")))
                currency = str(verification.get("currency") or "").upper()
            except Exception:
                result["errors"] += 1
                continue
            if currency != order.currency or abs(amount - Decimal(order.total_amount)) > Decimal("0.01"):
                # Divergence financière : jamais d'auto-fulfillment.
                result["errors"] += 1
                continue
            try:
                from .views import CheckoutView
                with transaction.atomic():
                    locked = Order.objects.select_for_update().get(pk=order_id)
                    if locked.status != Order.Status.PENDING:
                        continue
                    CheckoutView()._fulfill(locked)
                result["paid"] += 1
            except (Order.DoesNotExist, ValueError):
                result["errors"] += 1
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
                locked.save(update_fields=["status"])
                _release_failed_order_reservations(locked)
            result["failed"] += 1
        else:
            result["pending"] += 1

    return result
