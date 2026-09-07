from __future__ import annotations

from statistics import mean

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone


def _key(session_id: int) -> str:
    return f"live-quality:v91:{int(session_id)}"


def _number(value, *, minimum: float = 0.0, maximum: float = 1_000_000.0) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:  # NaN
        return None
    return max(minimum, min(number, maximum))


def normalize_quality_payload(payload: dict) -> dict:
    peers = int(_number(payload.get("peers"), minimum=0, maximum=100) or 0)
    rtt_ms = _number(payload.get("rtt_ms"), maximum=60_000)
    jitter_ms = _number(payload.get("jitter_ms"), maximum=60_000)
    packet_loss_pct = _number(payload.get("packet_loss_pct"), maximum=100)
    outgoing_kbps = _number(payload.get("outgoing_kbps"), maximum=1_000_000)
    quality = str(payload.get("quality") or "unknown").lower()
    if quality not in {"good", "fair", "poor", "unknown"}:
        quality = "unknown"
    return {
        "peers": peers,
        "rtt_ms": round(rtt_ms, 1) if rtt_ms is not None else None,
        "jitter_ms": round(jitter_ms, 1) if jitter_ms is not None else None,
        "packet_loss_pct": round(packet_loss_pct, 2) if packet_loss_pct is not None else None,
        "outgoing_kbps": round(outgoing_kbps, 1) if outgoing_kbps is not None else None,
        "quality": quality,
        "updated_at": timezone.now().isoformat(),
    }


def record_session_quality(*, session_id: int, user_id: int, payload: dict) -> dict:
    normalized = normalize_quality_payload(payload if isinstance(payload, dict) else {})
    key = _key(session_id)
    try:
        snapshot = cache.get(key) or {}
        if not isinstance(snapshot, dict):
            snapshot = {}
        snapshot[str(int(user_id))] = normalized
        ttl = max(int(getattr(settings, "RTC_QUALITY_TTL_SECONDS", 180)), 60)
        cache.set(key, snapshot, timeout=ttl)
    except Exception:
        # La qualité WebRTC est de l'observabilité : une panne Redis ne doit jamais
        # casser une salle ni transformer le cache en dépendance transactionnelle.
        pass
    return normalized


def session_quality_snapshot(session_id: int) -> dict:
    try:
        snapshot = cache.get(_key(session_id)) or {}
    except Exception:
        snapshot = {}
    if not isinstance(snapshot, dict):
        snapshot = {}
    rows = [row for row in snapshot.values() if isinstance(row, dict)]
    qualities = {"good": 0, "fair": 0, "poor": 0, "unknown": 0}
    for row in rows:
        quality = str(row.get("quality") or "unknown")
        qualities[quality if quality in qualities else "unknown"] += 1

    def avg(field: str):
        values = [float(row[field]) for row in rows if row.get(field) is not None]
        return round(mean(values), 2) if values else None

    return {
        "reports": len(rows),
        "quality": qualities,
        "avg_rtt_ms": avg("rtt_ms"),
        "avg_jitter_ms": avg("jitter_ms"),
        "avg_packet_loss_pct": avg("packet_loss_pct"),
        "avg_outgoing_kbps": avg("outgoing_kbps"),
        "participants": snapshot,
    }
