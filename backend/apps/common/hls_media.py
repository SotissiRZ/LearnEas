from __future__ import annotations

import posixpath
import re
from pathlib import PurePosixPath
from urllib.parse import quote

from django.core import signing

HLS_SALT = "learneas.hls-media"
HLS_ALLOWED_PREFIX = "courses/hls/"
_URI_ATTR_RE = re.compile(r'URI="([^"]+)"')


def _validate_hls_path(name: str) -> str:
    value = str(name or "").lstrip("/")
    normalized = posixpath.normpath(value)
    if not normalized.startswith(HLS_ALLOWED_PREFIX) or normalized.startswith("../") or "/../" in f"/{normalized}/":
        raise ValueError("Chemin HLS invalide")
    return normalized


def sign_hls_path(name: str) -> str:
    normalized = _validate_hls_path(name)
    token = signing.dumps({"name": normalized}, salt=HLS_SALT, compress=True)
    return f"/api/media/hls/?token={quote(token)}"


def unsign_hls_token(token: str, *, max_age: int) -> str:
    payload = signing.loads(token, salt=HLS_SALT, max_age=max_age)
    return _validate_hls_path(str(payload["name"]))


def resolve_hls_reference(playlist_name: str, reference: str) -> str:
    # Les manifests générés par LearnEas contiennent uniquement des références relatives.
    # On refuse volontairement les URL absolues pour empêcher un manifeste privé de devenir
    # un proxy vers un hôte tiers.
    raw = str(reference or "").strip()
    if not raw or "://" in raw or raw.startswith("//"):
        raise ValueError("Référence HLS externe interdite")
    base = posixpath.dirname(_validate_hls_path(playlist_name))
    joined = posixpath.normpath(posixpath.join(base, raw))
    return _validate_hls_path(joined)


def rewrite_hls_playlist(playlist_name: str, body: str) -> str:
    """Réécrit toutes les URI d'un manifeste vers des URL signées LearnEas."""
    output: list[str] = []
    for original_line in body.splitlines():
        line = original_line.strip()
        if not line:
            output.append(original_line)
            continue
        if line.startswith("#"):
            def replace_uri(match: re.Match[str]) -> str:
                target = resolve_hls_reference(playlist_name, match.group(1))
                return f'URI="{sign_hls_path(target)}"'
            output.append(_URI_ATTR_RE.sub(replace_uri, original_line))
            continue
        target = resolve_hls_reference(playlist_name, line)
        output.append(sign_hls_path(target))
    return "\n".join(output) + "\n"
