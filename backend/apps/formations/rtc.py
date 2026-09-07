from __future__ import annotations

import base64
import hashlib
import hmac
import time
from typing import Iterable

from django.conf import settings


def _split_urls(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        parts: Iterable[object] = value
    else:
        parts = str(value).split(",")
    seen: set[str] = set()
    urls: list[str] = []
    for raw in parts:
        item = str(raw or "").strip()
        if item and item not in seen:
            seen.add(item)
            urls.append(item)
    return urls


def ice_servers_for_user(user) -> list[dict]:
    """Construit la configuration ICE sans exposer de secret statique au bundle frontend.

    V91 accepte plusieurs STUN/TURN séparés par des virgules tout en conservant les
    variables historiques singulières. Les identifiants TURN REST coturn restent
    temporaires et liés à l'utilisateur.
    """

    stun_urls = _split_urls(getattr(settings, "RTC_STUN_URLS", "")) or _split_urls(
        getattr(settings, "RTC_STUN_URL", "")
    )
    turn_urls = _split_urls(getattr(settings, "RTC_TURN_URLS", "")) or _split_urls(
        getattr(settings, "RTC_TURN_URL", "")
    )

    servers: list[dict] = []
    if stun_urls:
        servers.append({"urls": stun_urls if len(stun_urls) > 1 else stun_urls[0]})
    if not turn_urls:
        return servers

    urls_value: str | list[str] = turn_urls if len(turn_urls) > 1 else turn_urls[0]
    secret = str(getattr(settings, "RTC_TURN_SECRET", "") or "")
    if secret:
        ttl = max(int(getattr(settings, "RTC_TURN_TTL_SECONDS", 3600)), 60)
        expires_at = int(time.time()) + ttl
        username = f"{expires_at}:{user.id}"
        credential = base64.b64encode(
            hmac.new(secret.encode("utf-8"), username.encode("utf-8"), hashlib.sha1).digest()
        ).decode("ascii")
        servers.append({"urls": urls_value, "username": username, "credential": credential})
        return servers

    # Compatibilité avec un fournisseur TURN qui ne prend pas en charge le secret REST coturn.
    username = str(getattr(settings, "RTC_TURN_USERNAME", "") or "")
    credential = str(getattr(settings, "RTC_TURN_CREDENTIAL", "") or "")
    if username and credential:
        servers.append({"urls": urls_value, "username": username, "credential": credential})
    return servers


def rtc_policy(*, active_participants: int = 0) -> dict:
    """Contrat stable de topologie WebRTC.

    V91 reste volontairement en mesh tant qu'aucun adaptateur SFU réel n'est branché.
    Le backend peut cependant signaler quand la topologie devrait évoluer, ce qui permet
    d'observer la charge réelle avant de déployer mediasoup/LiveKit/Janus ou équivalent.
    """

    mesh_soft_limit = max(int(getattr(settings, "RTC_MESH_SOFT_LIMIT", 6)), 2)
    sfu_threshold = max(int(getattr(settings, "RTC_SFU_RECOMMEND_THRESHOLD", mesh_soft_limit + 1)), 3)
    sfu_configured = bool(str(getattr(settings, "RTC_SFU_URL", "") or "").strip())
    participant_count = max(int(active_participants or 0), 0)
    recommended = participant_count >= sfu_threshold

    transport_policy = str(getattr(settings, "RTC_ICE_TRANSPORT_POLICY", "all") or "all").lower()
    if transport_policy not in {"all", "relay"}:
        transport_policy = "all"

    return {
        "topology": "mesh",
        "recommended_topology": "sfu" if recommended else "mesh",
        "sfu_configured": sfu_configured,
        "mesh_soft_limit": mesh_soft_limit,
        "sfu_recommend_threshold": sfu_threshold,
        "participant_count": participant_count,
        "ice_transport_policy": transport_policy,
        "ice_candidate_pool_size": max(0, min(int(getattr(settings, "RTC_ICE_CANDIDATE_POOL_SIZE", 2)), 16)),
        "disconnect_grace_seconds": max(3, min(int(getattr(settings, "RTC_DISCONNECT_GRACE_SECONDS", 8)), 30)),
        "quality_interval_seconds": max(5, min(int(getattr(settings, "RTC_QUALITY_INTERVAL_SECONDS", 10)), 60)),
        "video_max_bitrate_kbps": max(150, min(int(getattr(settings, "RTC_VIDEO_MAX_BITRATE_KBPS", 900)), 4000)),
        "audio_max_bitrate_kbps": max(24, min(int(getattr(settings, "RTC_AUDIO_MAX_BITRATE_KBPS", 64)), 256)),
    }
