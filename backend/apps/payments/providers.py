import json
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal
from django.conf import settings
import stripe

from .models import Currency


class ProviderError(Exception):
    pass


def _request_json(url, method="GET", headers=None, data=None, timeout=12):
    headers = {"Accept": "application/json", **(headers or {})}
    body = None
    if data is not None:
        if headers.get("Content-Type") == "application/json":
            body = json.dumps(data).encode("utf-8")
        else:
            body = urllib.parse.urlencode(data).encode("utf-8")
            headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
            message = payload.get("message") or payload.get("error") or payload.get("detail") or raw
        except Exception:
            message = raw or str(exc)
        raise ProviderError(f"Prestataire: {message}") from exc
    except Exception as exc:
        raise ProviderError(f"Prestataire injoignable: {exc}") from exc


def _stripe_key(sandbox: bool) -> str:
    if sandbox:
        test_key = getattr(settings, "STRIPE_TEST_SECRET_KEY", "")
        # Compatibilité pratique : une clé explicitement Stripe TEST placée dans l'ancienne
        # variable peut être utilisée en sandbox, mais une clé live n'est jamais réutilisée.
        legacy = getattr(settings, "STRIPE_SECRET_KEY", "")
        return test_key or (legacy if str(legacy).startswith("sk_test_") else "")
    live_key = getattr(settings, "STRIPE_SECRET_KEY", "")
    return live_key if not str(live_key).startswith("sk_test_") else ""


def _youcan_config(sandbox: bool) -> tuple[str, str]:
    if sandbox:
        token = getattr(settings, "YOUCANPAY_SANDBOX_ACCESS_TOKEN", "")
        base = getattr(settings, "YOUCANPAY_SANDBOX_API_BASE", "") or getattr(settings, "YOUCANPAY_API_BASE", "https://youcanpay.com/api/v2")
    else:
        token = getattr(settings, "YOUCANPAY_ACCESS_TOKEN", "")
        base = getattr(settings, "YOUCANPAY_API_BASE", "https://youcanpay.com/api/v2")
    return token, base.rstrip("/")


def _genius_config(sandbox: bool) -> tuple[str, str, str]:
    if sandbox:
        api_key = getattr(settings, "GENIUSPAY_SANDBOX_API_KEY", "")
        api_secret = getattr(settings, "GENIUSPAY_SANDBOX_API_SECRET", "")
        base = getattr(settings, "GENIUSPAY_SANDBOX_API_BASE", "") or getattr(settings, "GENIUSPAY_API_BASE", "https://geniuspay.ci/api/v1/merchant")
    else:
        api_key = getattr(settings, "GENIUSPAY_API_KEY", "")
        api_secret = getattr(settings, "GENIUSPAY_API_SECRET", "")
        base = getattr(settings, "GENIUSPAY_API_BASE", "https://geniuspay.ci/api/v1/merchant")
    return api_key, api_secret, base.rstrip("/")



def _currency_scale(code: str) -> Decimal:
    """Facteur entre unité majeure et unité mineure configurée (MAD=100, XOF=1)."""
    places = Currency.objects.filter(code=str(code).upper()).values_list("decimal_places", flat=True).first()
    if places is None:
        places = 2
    places = max(0, min(int(places), 2))
    return Decimal(10) ** places


def _to_minor_units(amount: Decimal, currency: str) -> int:
    return int((Decimal(amount) * _currency_scale(currency)).quantize(Decimal("1")))


def _from_minor_units(amount, currency: str) -> Decimal:
    return Decimal(str(amount or 0)) / _currency_scale(currency)


def is_configured(code: str, *, sandbox: bool = False) -> bool:
    if code == "stripe":
        return bool(_stripe_key(sandbox))
    if code == "youcanpay":
        return bool(_youcan_config(sandbox)[0])
    if code == "geniuspay":
        api_key, api_secret, _ = _genius_config(sandbox)
        return bool(api_key and api_secret)
    if code == "manual":
        return True
    return False

def create_checkout(order, user):
    """Crée une session de paiement hébergée et retourne (url, reference)."""
    code = order.provider
    sandbox = bool(getattr(order, "provider_sandbox", False))
    amount_minor = _to_minor_units(Decimal(order.total_amount), order.currency)
    success_url = f"{settings.FRONTEND_URL}/dashboard/student?purchased=1&order={order.id}"
    cancel_url = f"{settings.FRONTEND_URL}/checkout?cancelled=1"

    if code == "stripe":
        secret_key = _stripe_key(sandbox)
        if not secret_key:
            raise ProviderError("Stripe n'est pas configuré pour cet environnement.")
        stripe.api_key = secret_key
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": order.currency.lower(),
                    "product_data": {"name": f"Commande LearnEas {order.invoice_number}"},
                    "unit_amount": amount_minor,
                },
                "quantity": 1,
            }],
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=str(order.id),
            metadata={"order_id": str(order.id), "user_id": str(user.id)},
        )
        return session.url, session.id

    if code == "youcanpay":
        token, base = _youcan_config(sandbox)
        if not token:
            raise ProviderError("YouCan Pay n'est pas configuré pour cet environnement.")
        payload = _request_json(
            f"{base}/invoices",
            method="POST",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "reference": order.invoice_number,
                "name": f"Commande LearnEas {order.invoice_number}",
                "amount": amount_minor,
                "currency": order.currency.upper(),
                "description": f"Achat LearnEas #{order.id}",
                "active": "1",
            },
        )
        checkout_url = payload.get("link")
        reference = payload.get("id") or payload.get("reference")
        if not checkout_url or not reference:
            raise ProviderError("YouCan Pay n'a pas retourné de lien de paiement valide.")
        return checkout_url, str(reference)

    if code == "geniuspay":
        api_key, api_secret, base = _genius_config(sandbox)
        if not api_key or not api_secret:
            raise ProviderError("GeniusPay n'est pas configuré pour cet environnement.")
        payload = _request_json(
            f"{base}/payments",
            method="POST",
            headers={"X-API-Key": api_key, "X-API-Secret": api_secret, "Content-Type": "application/json"},
            data={
                "amount": float(order.total_amount),
                "currency": order.currency.upper(),
                "description": f"Commande LearnEas {order.invoice_number}",
                "customer": {"name": user.get_full_name() or user.username, "email": user.email},
                "success_url": success_url,
                "error_url": cancel_url,
                "metadata": {"order_id": str(order.id), "user_id": str(user.id)},
            },
        )
        data = payload.get("data") or payload
        checkout_url = data.get("checkout_url") or data.get("payment_url")
        reference = data.get("reference") or data.get("id")
        if not checkout_url or reference is None:
            raise ProviderError("GeniusPay n'a pas retourné de lien de paiement valide.")
        return checkout_url, str(reference)

    if code == "manual":
        raise ProviderError("Le paiement manuel doit être validé par un administrateur.")
    raise ProviderError("Moyen de paiement inconnu.")


def test_provider(code: str, *, sandbox: bool = False):
    """Test non transactionnel : aucune vraie charge n'est créée."""
    if code == "stripe":
        secret_key = _stripe_key(sandbox)
        if not secret_key:
            raise ProviderError("Clé Stripe absente pour cet environnement.")
        stripe.api_key = secret_key
        balance = stripe.Balance.retrieve()
        return {"ok": True, "detail": "Connexion Stripe valide.", "livemode": bool(getattr(balance, "livemode", False))}
    if code == "youcanpay":
        token, base = _youcan_config(sandbox)
        if not token:
            raise ProviderError("Token YouCan Pay absent pour cet environnement.")
        _request_json(f"{base}/transactions?limit=1", headers={"Authorization": f"Bearer {token}"})
        return {"ok": True, "detail": "Connexion YouCan Pay valide."}
    if code == "geniuspay":
        api_key, api_secret, base = _genius_config(sandbox)
        if not api_key or not api_secret:
            raise ProviderError("Clés GeniusPay absentes pour cet environnement.")
        # La liste des paiements est un diagnostic en lecture seule et n'initie aucune transaction.
        payload = _request_json(f"{base}/payments?per_page=1", headers={"X-API-Key": api_key, "X-API-Secret": api_secret})
        return {"ok": True, "detail": "Connexion GeniusPay valide.", "environment": "sandbox" if sandbox else "live", "reachable": bool(payload is not None)}
    if code == "manual":
        return {"ok": True, "detail": "Paiement manuel disponible (aucune API externe)."}
    raise ProviderError("Prestataire inconnu.")

def verify_payment(order):
    """Vérifie côté serveur l'état du paiement sans faire confiance au navigateur."""
    sandbox = bool(getattr(order, "provider_sandbox", False))
    if order.provider == "youcanpay":
        token, base = _youcan_config(sandbox)
        if not token or not order.provider_reference:
            raise ProviderError("YouCan Pay n'est pas configuré pour cet environnement ou la référence est absente.")
        payload = _request_json(f"{base}/invoices/{urllib.parse.quote(str(order.provider_reference))}", headers={"Authorization": f"Bearer {token}"})
        amount = payload.get("amount") or {}
        paid = payload.get("status") == "paid"
        return {
            "paid": paid,
            "amount": Decimal(str(amount.get("amount", "0"))) if amount else Decimal("0"),
            "currency": str(amount.get("currency") or "").upper(),
        }
    if order.provider == "geniuspay":
        api_key, api_secret, base = _genius_config(sandbox)
        if not api_key or not api_secret or not order.provider_reference:
            raise ProviderError("GeniusPay n'est pas configuré pour cet environnement ou la référence est absente.")
        payload = _request_json(f"{base}/payments/{urllib.parse.quote(str(order.provider_reference))}", headers={"X-API-Key": api_key, "X-API-Secret": api_secret})
        data = payload.get("data") or payload
        status = str(data.get("status") or "").lower()
        return {
            "paid": status in {"paid", "success", "completed"},
            "amount": Decimal(str(data.get("amount", "0"))),
            "currency": str(data.get("currency") or "").upper(),
        }
    if order.provider == "stripe":
        secret_key = _stripe_key(sandbox)
        if not secret_key or not order.provider_reference:
            raise ProviderError("Stripe n'est pas configuré pour cet environnement ou la référence est absente.")
        stripe.api_key = secret_key
        session = stripe.checkout.Session.retrieve(order.provider_reference)
        return {
            "paid": str(getattr(session, "payment_status", "")) == "paid",
            "amount": _from_minor_units(getattr(session, "amount_total", 0), order.currency),
            "currency": str(getattr(session, "currency", "")).upper(),
        }
    raise ProviderError("Ce prestataire ne permet pas de confirmation automatique.")
