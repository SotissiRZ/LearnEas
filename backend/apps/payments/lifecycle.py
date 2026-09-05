"""Primitives opérationnelles du cycle de paiement KalanPro.

Le module ne contacte jamais un prestataire et n'attribue aucun entitlement. Il centralise
l'audit, la redaction, les snapshots de vérification et les anomalies financières afin que
checkout, webhooks, confirmation utilisateur et réconciliation appliquent les mêmes règles.
"""
from __future__ import annotations

import hashlib
import json
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from .models import Order, PaymentAttempt, PaymentEvent, PaymentIssue

MONEY_TOLERANCE = Decimal("0.01")
_SENSITIVE_MARKERS = (
    "phone", "email", "name", "surname", "address", "token", "secret", "signature",
    "authorization", "card", "account", "customer", "credential", "password", "cel_",
)
_ALLOWED_LONG_KEYS = {"description", "message", "status", "payment_method", "currency", "amount", "code"}


def _safe_scalar(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    text = str(value)
    return text[:500]


def redact_payload(value: Any, *, key: str = "") -> Any:
    """Copie JSON-safe en supprimant les champs susceptibles de contenir des PII/secrets."""
    normalized_key = str(key or "").lower()
    if normalized_key and any(marker in normalized_key for marker in _SENSITIVE_MARKERS):
        return "[redacted]"
    if isinstance(value, dict):
        return {str(k)[:100]: redact_payload(v, key=str(k)) for k, v in list(value.items())[:80]}
    if isinstance(value, (list, tuple)):
        return [redact_payload(item) for item in list(value)[:80]]
    scalar = _safe_scalar(value)
    if isinstance(scalar, str) and len(scalar) > 200 and normalized_key not in _ALLOWED_LONG_KEYS:
        return scalar[:200] + "…"
    return scalar


def payload_hash(payload: Any) -> str:
    try:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    except Exception:
        raw = str(payload).encode("utf-8", errors="replace")
    return hashlib.sha256(raw).hexdigest()


def record_event(
    *,
    order: Order | None,
    source: str,
    event_type: str,
    outcome: str = PaymentEvent.Outcome.RECEIVED,
    provider: str = "",
    provider_sandbox: bool | None = None,
    external_id: str = "",
    payload: Any = None,
    request_id: str = "",
    message: str = "",
) -> tuple[PaymentEvent, bool]:
    """Ajoute un événement append-only. Retourne (event, created).

    `external_id` rend les webhooks persistamment idempotents, même après redémarrage Redis.
    """
    provider = str(provider or (order.provider if order else ""))[:30]
    sandbox = bool(provider_sandbox if provider_sandbox is not None else getattr(order, "provider_sandbox", False))
    external_id = str(external_id or "")[:191]
    cleaned = redact_payload(payload or {})
    digest = payload_hash(payload or {})
    defaults = {
        "order": order,
        "source": source,
        "event_type": str(event_type)[:100],
        "outcome": outcome,
        "payload_hash": digest,
        "payload": cleaned,
        "request_id": str(request_id or "")[:100],
        "message": str(message or "")[:500],
    }
    if external_id:
        try:
            with transaction.atomic():
                event, created = PaymentEvent.objects.get_or_create(
                    provider=provider,
                    provider_sandbox=sandbox,
                    external_id=external_id,
                    defaults=defaults,
                )
            return event, created
        except IntegrityError:
            return PaymentEvent.objects.get(
                provider=provider, provider_sandbox=sandbox, external_id=external_id
            ), False
    return PaymentEvent.objects.create(
        provider=provider,
        provider_sandbox=sandbox,
        external_id="",
        **defaults,
    ), True


def create_attempt(order: Order) -> PaymentAttempt:
    last = order.payment_attempts.order_by("-attempt_number").values_list("attempt_number", flat=True).first() or 0
    number = int(last) + 1
    try:
        with transaction.atomic():
            return PaymentAttempt.objects.create(
                order=order,
                attempt_number=number,
                provider=order.provider,
                provider_sandbox=order.provider_sandbox,
                provider_reference=order.provider_reference,
                status=PaymentAttempt.Status.CREATED,
                amount=order.total_amount,
                currency=order.currency,
            )
    except IntegrityError:
        # Une commande historique sans tentative peut être vérifiée simultanément par un
        # webhook et la réconciliation. La contrainte DB arbitre ; le perdant réutilise la
        # tentative déjà créée au lieu d'échouer.
        existing = order.payment_attempts.order_by("-attempt_number").first()
        if existing:
            return existing
        raise


def current_attempt(order: Order, *, create: bool = True) -> PaymentAttempt | None:
    attempt = order.payment_attempts.order_by("-attempt_number").first()
    if attempt is None and create:
        attempt = create_attempt(order)
    return attempt


def mark_attempt_redirected(order: Order, *, reference: str = "") -> PaymentAttempt:
    attempt = current_attempt(order)
    attempt.provider_reference = str(reference or order.provider_reference or "")[:255]
    attempt.status = PaymentAttempt.Status.REDIRECTED
    attempt.save(update_fields=["provider_reference", "status", "updated_at"])
    return attempt


def register_provider_error(order: Order, message: str, *, source: str, request_id: str = "") -> int:
    now = timezone.now()
    attempt = current_attempt(order)
    PaymentAttempt.objects.filter(pk=attempt.pk).update(
        error_count=F("error_count") + 1,
        last_error=str(message or "")[:500],
        last_checked_at=now,
        status=PaymentAttempt.Status.ERROR,
    )
    attempt.refresh_from_db(fields=["error_count"])
    order.last_provider_check_at = now
    order.save(update_fields=["last_provider_check_at"])
    record_event(
        order=order, source=source, event_type="provider.error", outcome=PaymentEvent.Outcome.ERROR,
        request_id=request_id, message=message,
    )
    if attempt.error_count >= 3:
        open_issue(
            order,
            PaymentIssue.IssueType.PROVIDER_ERROR,
            message="Le prestataire de paiement a échoué au moins trois fois lors des vérifications.",
            severity=PaymentIssue.Severity.WARNING,
            observed={"error_count": attempt.error_count, "last_error": str(message or "")[:200]},
        )
    return attempt.error_count


def _decimal(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def update_verification_snapshot(order: Order, verification: dict[str, Any]) -> PaymentAttempt:
    now = timezone.now()
    provider_status = str(verification.get("status") or ("PAID" if verification.get("paid") else "PENDING"))[:80]
    payment_method = str(verification.get("payment_method") or "")[:80]
    Order.objects.filter(pk=order.pk).update(
        provider_status=provider_status,
        payment_method=payment_method,
        last_provider_check_at=now,
    )
    order.provider_status = provider_status
    order.payment_method = payment_method
    order.last_provider_check_at = now

    attempt = current_attempt(order)
    # Une réponse prestataire "paid" reste une simple vérification tant que montant/devise
    # n'ont pas été validés. Le statut PAID n'est posé qu'après fulfillment cohérent.
    status = PaymentAttempt.Status.CHECKED
    PaymentAttempt.objects.filter(pk=attempt.pk).update(
        provider_status=provider_status,
        payment_method=payment_method,
        check_count=F("check_count") + 1,
        last_checked_at=now,
        status=status,
    )
    attempt.refresh_from_db()
    return attempt


def open_issue(
    order: Order,
    issue_type: str,
    *,
    message: str,
    severity: str = PaymentIssue.Severity.WARNING,
    expected: dict | None = None,
    observed: dict | None = None,
) -> PaymentIssue:
    defaults = {
        "severity": severity,
        "message": str(message)[:500],
        "expected": redact_payload(expected or {}),
        "observed": redact_payload(observed or {}),
    }
    try:
        with transaction.atomic():
            issue, created = PaymentIssue.objects.get_or_create(
                order=order,
                issue_type=issue_type,
                status=PaymentIssue.Status.OPEN,
                defaults=defaults,
            )
    except IntegrityError:
        issue = PaymentIssue.objects.get(
            order=order, issue_type=issue_type, status=PaymentIssue.Status.OPEN
        )
        created = False
    if not created:
        issue.severity = severity
        issue.message = str(message)[:500]
        issue.expected = redact_payload(expected or {})
        issue.observed = redact_payload(observed or {})
        issue.save(update_fields=["severity", "message", "expected", "observed"])
    return issue


def resolve_order_issues(order: Order, types: list[str] | tuple[str, ...], note: str) -> None:
    now = timezone.now()
    PaymentIssue.objects.filter(
        order=order, issue_type__in=list(types), status=PaymentIssue.Status.OPEN
    ).update(status=PaymentIssue.Status.RESOLVED, resolved_at=now, resolution_note=str(note or "")[:500])


def classify_verification(order: Order, verification: dict[str, Any]) -> str:
    """Retourne paid / pending / amount_mismatch / currency_mismatch.

    Les statuts terminaux refusés restent gérés par l'appelant car CinetPay a une sémantique
    particulière pour REFUSED.
    """
    update_verification_snapshot(order, verification)
    resolve_order_issues(
        order, (PaymentIssue.IssueType.PROVIDER_ERROR,),
        "Le prestataire répond de nouveau correctement.",
    )
    if not verification.get("paid"):
        return "pending"
    amount = _decimal(verification.get("amount"))
    currency = str(verification.get("currency") or "").upper()
    expected_amount = Decimal(order.total_amount)
    if currency != order.currency:
        open_issue(
            order, PaymentIssue.IssueType.CURRENCY_MISMATCH,
            severity=PaymentIssue.Severity.CRITICAL,
            message="La devise confirmée par le prestataire ne correspond pas à la commande.",
            expected={"currency": order.currency, "amount": str(expected_amount)},
            observed={"currency": currency, "amount": str(amount) if amount is not None else None},
        )
        return "currency_mismatch"
    if amount is None or abs(amount - expected_amount) > MONEY_TOLERANCE:
        open_issue(
            order, PaymentIssue.IssueType.AMOUNT_MISMATCH,
            severity=PaymentIssue.Severity.CRITICAL,
            message="Le montant confirmé par le prestataire ne correspond pas à la commande.",
            expected={"currency": order.currency, "amount": str(expected_amount)},
            observed={"currency": currency, "amount": str(amount) if amount is not None else None},
        )
        return "amount_mismatch"
    resolve_order_issues(
        order,
        (PaymentIssue.IssueType.AMOUNT_MISMATCH, PaymentIssue.IssueType.CURRENCY_MISMATCH, PaymentIssue.IssueType.PROVIDER_ERROR),
        "Vérification prestataire cohérente.",
    )
    return "paid"


def mark_attempt_paid(order: Order, verification: dict[str, Any] | None = None) -> None:
    now = timezone.now()
    attempt = current_attempt(order)
    fields = {
        "status": PaymentAttempt.Status.PAID,
        "completed_at": now,
        "last_checked_at": now,
    }
    if verification:
        fields["provider_status"] = str(verification.get("status") or "PAID")[:80]
        fields["payment_method"] = str(verification.get("payment_method") or "")[:80]
    PaymentAttempt.objects.filter(pk=attempt.pk).update(**fields)


def mark_attempt_failed(order: Order, provider_status: str = "FAILED", message: str = "") -> None:
    now = timezone.now()
    attempt = current_attempt(order)
    PaymentAttempt.objects.filter(pk=attempt.pk).update(
        status=PaymentAttempt.Status.FAILED,
        provider_status=str(provider_status or "FAILED")[:80],
        last_error=str(message or "")[:500],
        completed_at=now,
        last_checked_at=now,
    )
    Order.objects.filter(pk=order.pk).update(
        provider_status=str(provider_status or "FAILED")[:80],
        last_provider_check_at=now,
    )
