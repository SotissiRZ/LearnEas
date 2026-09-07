from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from django.conf import settings


def _value(name: str, default: Any = "") -> Any:
    return getattr(settings, name, default)


def _text(name: str) -> str:
    return str(_value(name, "") or "").strip()


def _bool(name: str, default: bool = False) -> bool:
    return bool(_value(name, default))


def _origin(value: str) -> str:
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return ""
        port = f":{parsed.port}" if parsed.port else ""
        return f"{parsed.scheme}://{parsed.hostname}{port}"
    except Exception:
        return ""


def _hostname(value: str) -> str:
    try:
        return str(urlsplit(value).hostname or "").lower()
    except Exception:
        return ""


def _https(value: str) -> bool:
    return bool(value and _origin(value).startswith("https://"))


def _nonlocal_url(value: str) -> bool:
    host = _hostname(value)
    return bool(host and host not in {"localhost", "127.0.0.1", "0.0.0.0"} and not host.endswith(".local"))


def _configured_payment_providers() -> dict[str, bool]:
    return {
        "stripe": bool(_text("STRIPE_SECRET_KEY") and _text("STRIPE_WEBHOOK_SECRET")),
        "youcanpay": bool(_text("YOUCANPAY_ACCESS_TOKEN")),
        "geniuspay": bool(
            _text("GENIUSPAY_API_KEY")
            and _text("GENIUSPAY_API_SECRET")
            and _text("GENIUSPAY_WEBHOOK_SECRET")
        ),
        "cinetpay": bool(
            _text("CINETPAY_API_KEY")
            and _text("CINETPAY_SITE_ID")
            and _text("CINETPAY_SECRET_KEY")
        ),
    }


def _transactional_email_state() -> dict[str, Any]:
    resend = _bool("RESEND_ENABLED")
    resend_ready = bool(resend and not _bool("RESEND_DRY_RUN", True) and _text("RESEND_API_KEY"))
    backend = _text("EMAIL_BACKEND")
    smtp = backend.endswith("smtp.EmailBackend")
    smtp_ready = bool(smtp and _text("EMAIL_HOST") and _text("EMAIL_HOST_USER") and _text("EMAIL_HOST_PASSWORD"))
    return {
        "resend_enabled": resend,
        "resend_dry_run": _bool("RESEND_DRY_RUN", True),
        "resend_ready": resend_ready,
        "smtp_ready": smtp_ready,
        "ready": resend_ready or smtp_ready,
    }


def _whatsapp_state() -> dict[str, Any]:
    enabled = _bool("WHATSAPP_ENABLED")
    dry_run = _bool("WHATSAPP_DRY_RUN", True)
    ready = bool(
        enabled
        and not dry_run
        and _text("WHATSAPP_PHONE_NUMBER_ID")
        and _text("WHATSAPP_ACCESS_TOKEN")
        and _text("WHATSAPP_VERIFY_TOKEN")
        and _text("WHATSAPP_APP_SECRET")
    )
    return {"enabled": enabled, "dry_run": dry_run, "ready": ready}


def build_production_preflight_snapshot() -> dict[str, Any]:
    """Validate the production contract without making external network calls.

    This is deliberately configuration-only so it can run during CI and before a
    Railway deployment. Runtime dependencies are covered separately by
    ``release_gate --strict-infra --deploy``.
    """

    blockers: list[str] = []
    warnings: list[str] = []

    frontend_url = _text("FRONTEND_URL")
    backend_url = _text("BACKEND_PUBLIC_URL")
    frontend_origin = _origin(frontend_url)
    backend_host = _hostname(backend_url)

    if _bool("DEBUG", True):
        blockers.append("debug_enabled")
    if not _bool("USE_HTTPS", False):
        blockers.append("https_disabled")
    for name, value in (("frontend_url", frontend_url), ("backend_public_url", backend_url)):
        if not _https(value) or not _nonlocal_url(value):
            blockers.append(f"invalid_{name}")

    if not _text("DATABASE_URL") or "localhost" in _text("DATABASE_URL").lower():
        blockers.append("database_url_not_production")
    if not _text("REDIS_URL") or "localhost" in _text("REDIS_URL").lower():
        blockers.append("redis_url_not_production")

    allowed_hosts = {str(x).strip().lower() for x in _value("ALLOWED_HOSTS", []) if str(x).strip()}
    if not backend_host or backend_host not in allowed_hosts:
        blockers.append("backend_host_missing_from_allowed_hosts")
    if "*" in allowed_hosts:
        blockers.append("wildcard_allowed_hosts")

    cors = {_origin(str(x).strip()) for x in _value("CORS_ALLOWED_ORIGINS", []) if str(x).strip()}
    csrf = {_origin(str(x).strip()) for x in _value("CSRF_TRUSTED_ORIGINS", []) if str(x).strip()}
    realtime = {_origin(str(x).strip()) for x in _value("REALTIME_ALLOWED_ORIGINS", []) if str(x).strip()}
    if not frontend_origin or frontend_origin not in cors:
        blockers.append("frontend_missing_from_cors")
    if not frontend_origin or frontend_origin not in csrf:
        blockers.append("frontend_missing_from_csrf")
    if not frontend_origin or frontend_origin not in realtime:
        blockers.append("frontend_missing_from_realtime_origins")

    if not _bool("AUTH_REFRESH_COOKIE_SECURE"):
        blockers.append("refresh_cookie_not_secure")
    if _text("AUTH_REFRESH_COOKIE_SAMESITE").lower() not in {"lax", "strict", "none"}:
        blockers.append("invalid_refresh_cookie_samesite")

    storage = {
        "use_s3": _bool("USE_S3"),
        "remote_required": _bool("REQUIRE_REMOTE_MEDIA"),
        "bucket": bool(_text("AWS_STORAGE_BUCKET_NAME")),
        "access_key": bool(_text("AWS_ACCESS_KEY_ID")),
        "secret_key": bool(_text("AWS_SECRET_ACCESS_KEY")),
        "direct_uploads": _bool("DIRECT_MEDIA_UPLOADS_ENABLED"),
        "public_cdn": bool(_text("PUBLIC_MEDIA_BASE_URL")),
    }
    if not all((storage["use_s3"], storage["remote_required"], storage["bucket"], storage["access_key"], storage["secret_key"])):
        blockers.append("remote_media_incomplete")
    if not storage["direct_uploads"]:
        blockers.append("direct_media_uploads_disabled")
    if not storage["public_cdn"]:
        warnings.append("public_media_cdn_not_configured")

    require_malware = _bool("PRODUCTION_REQUIRE_MALWARE_SCAN", True)
    malware = {
        "enabled": _bool("MALWARE_SCAN_ENABLED"),
        "required": _bool("MALWARE_SCAN_REQUIRED"),
        "host": bool(_text("CLAMAV_HOST")),
    }
    if require_malware and not all(malware.values()):
        blockers.append("malware_scan_incomplete")

    providers = _configured_payment_providers()
    if _bool("PRODUCTION_REQUIRE_PAYMENT_PROVIDER", True) and not any(providers.values()):
        blockers.append("payment_provider_missing")
    if _bool("TEST_PAYMENTS_ENABLED"):
        blockers.append("test_payments_enabled")

    email = _transactional_email_state()
    if _bool("PRODUCTION_REQUIRE_EMAIL", True) and not email["ready"]:
        blockers.append("transactional_email_not_ready")
    if email["resend_enabled"] and email["resend_dry_run"]:
        blockers.append("resend_dry_run_enabled")

    whatsapp = _whatsapp_state()
    if whatsapp["enabled"] and not whatsapp["ready"]:
        blockers.append("whatsapp_enabled_but_not_ready")

    turn_urls = _text("RTC_TURN_URLS") or _text("RTC_TURN_URL")
    turn_credentials = bool(_text("RTC_TURN_SECRET") or (_text("RTC_TURN_USERNAME") and _text("RTC_TURN_CREDENTIAL")))
    if _bool("PRODUCTION_REQUIRE_TURN", True) and not (turn_urls and turn_credentials):
        blockers.append("turn_not_ready")

    if not _text("RTC_SFU_URL"):
        warnings.append("sfu_not_configured_mesh_remains_active")

    ai_ready = bool(_text("AI_API_KEY") and _text("AI_CHAT_MODEL") and not _bool("AI_DRY_RUN", False))
    if not ai_ready:
        warnings.append("ai_provider_not_fully_configured")

    if _text("DEFAULT_FROM_EMAIL").lower().endswith("@kalanpro.com>") and "example" in frontend_url.lower():
        warnings.append("default_sender_domain_unverified")

    return {
        "status": "ok" if not blockers else "error",
        "environment": "production",
        "urls": {
            "frontend": frontend_url,
            "backend": backend_url,
            "same_origin_api_expected": True,
        },
        "storage": storage,
        "malware": malware,
        "payments": providers,
        "email": email,
        "whatsapp": whatsapp,
        "turn": {"configured": bool(turn_urls and turn_credentials)},
        "ai": {"configured": ai_ready},
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
    }
