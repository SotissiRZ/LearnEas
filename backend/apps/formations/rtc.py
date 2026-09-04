from __future__ import annotations

import base64
import hashlib
import hmac
import time

from django.conf import settings


def ice_servers_for_user(user) -> list[dict]:
    servers: list[dict] = []
    stun_url = str(getattr(settings, "RTC_STUN_URL", "") or "").strip()
    if stun_url:
        servers.append({"urls": stun_url})

    turn_url = str(getattr(settings, "RTC_TURN_URL", "") or "").strip()
    if not turn_url:
        return servers

    secret = str(getattr(settings, "RTC_TURN_SECRET", "") or "")
    if secret:
        ttl = max(int(getattr(settings, "RTC_TURN_TTL_SECONDS", 3600)), 60)
        expires_at = int(time.time()) + ttl
        username = f"{expires_at}:{user.id}"
        credential = base64.b64encode(
            hmac.new(secret.encode("utf-8"), username.encode("utf-8"), hashlib.sha1).digest()
        ).decode("ascii")
        servers.append({"urls": turn_url, "username": username, "credential": credential})
        return servers

    # Compatibilité avec un fournisseur TURN qui ne prend pas en charge le secret REST coturn.
    # Ces identifiants restent côté serveur et ne sont jamais intégrés au bundle Next.js.
    username = str(getattr(settings, "RTC_TURN_USERNAME", "") or "")
    credential = str(getattr(settings, "RTC_TURN_CREDENTIAL", "") or "")
    if username and credential:
        servers.append({"urls": turn_url, "username": username, "credential": credential})
    return servers
