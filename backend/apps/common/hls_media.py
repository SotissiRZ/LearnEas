from __future__ import annotations

import posixpath
import re
from pathlib import PurePosixPath
from urllib.parse import quote

from django.core import signing

HLS_SALT = "learneas.hls-media"
HLS_ALLOWED_PREFIX = "courses/hls/"
_URI_ATTR_RE = re.compile(r'URI="([^"]+)"')
_RESOLUTION_RE = re.compile(r"RESOLUTION=\d+x(\d+)", re.IGNORECASE)
_NAME_HEIGHT_RE = re.compile(r'NAME="?(\d{2,4})p"?', re.IGNORECASE)


def _validate_hls_path(name: str) -> str:
    value = str(name or "").lstrip("/")
    normalized = posixpath.normpath(value)
    if not normalized.startswith(HLS_ALLOWED_PREFIX) or normalized.startswith("../") or "/../" in f"/{normalized}/":
        raise ValueError("Chemin HLS invalide")
    return normalized


def _normalize_max_height(value) -> int | None:
    if value in (None, "", 0, "0"):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if 120 <= parsed <= 4320 else None


def sign_hls_path(name: str, *, max_height: int | None = None) -> str:
    """Signe un chemin HLS privé.

    ``max_height`` est une politique de lecture transportée dans le jeton. Elle permet de
    servir, depuis le même master stocké, une vue faible-débit (ex. <=360p) y compris aux
    navigateurs Safari qui utilisent leur moteur HLS natif et ne peuvent pas être plafonnés
    par hls.js.
    """
    normalized = _validate_hls_path(name)
    payload: dict[str, object] = {"name": normalized}
    safe_height = _normalize_max_height(max_height)
    if safe_height:
        payload["max_height"] = safe_height
    token = signing.dumps(payload, salt=HLS_SALT, compress=True)
    return f"/api/media/hls/?token={quote(token)}"


def unsign_hls_token_payload(token: str, *, max_age: int) -> tuple[str, int | None]:
    payload = signing.loads(token, salt=HLS_SALT, max_age=max_age)
    name = _validate_hls_path(str(payload["name"]))
    return name, _normalize_max_height(payload.get("max_height"))


def unsign_hls_token(token: str, *, max_age: int) -> str:
    """Compatibilité avec les appels/tests historiques qui n'ont besoin que du chemin."""
    name, _max_height = unsign_hls_token_payload(token, max_age=max_age)
    return name


def resolve_hls_reference(playlist_name: str, reference: str) -> str:
    # Les manifests générés par KalanPro contiennent uniquement des références relatives.
    # On refuse volontairement les URL absolues pour empêcher un manifeste privé de devenir
    # un proxy vers un hôte tiers.
    raw = str(reference or "").strip()
    if not raw or "://" in raw or raw.startswith("//"):
        raise ValueError("Référence HLS externe interdite")
    base = posixpath.dirname(_validate_hls_path(playlist_name))
    joined = posixpath.normpath(posixpath.join(base, raw))
    return _validate_hls_path(joined)


def _stream_height(stream_inf: str) -> int | None:
    match = _RESOLUTION_RE.search(stream_inf) or _NAME_HEIGHT_RE.search(stream_inf)
    if not match:
        return None
    try:
        return int(match.group(1))
    except (TypeError, ValueError):
        return None


def _filter_master_by_height(lines: list[str], max_height: int | None) -> list[str]:
    """Filtre uniquement les couples EXT-X-STREAM-INF + URI d'un master HLS.

    Les playlists de variante ne contiennent pas ``#EXT-X-STREAM-INF`` et passent donc
    inchangées. Si un ancien master ne contient aucune variante sous la limite, on conserve
    la variante la plus basse au lieu de produire un manifeste vide.
    """
    if not max_height or not any(line.strip().startswith("#EXT-X-STREAM-INF") for line in lines):
        return lines

    prefix: list[str] = []
    variants: list[tuple[str, str, int | None]] = []
    suffix: list[str] = []
    seen_variant = False
    index = 0
    while index < len(lines):
        original = lines[index]
        stripped = original.strip()
        if stripped.startswith("#EXT-X-STREAM-INF"):
            seen_variant = True
            uri_index = index + 1
            while uri_index < len(lines) and not lines[uri_index].strip():
                uri_index += 1
            if uri_index < len(lines) and not lines[uri_index].strip().startswith("#"):
                variants.append((original, lines[uri_index], _stream_height(stripped)))
                index = uri_index + 1
                continue
        if not seen_variant:
            prefix.append(original)
        else:
            suffix.append(original)
        index += 1

    if not variants:
        return lines

    kept = [variant for variant in variants if variant[2] is None or variant[2] <= max_height]
    if not kept:
        kept = [min(variants, key=lambda item: item[2] if item[2] is not None else 10_000)]

    output = list(prefix)
    for stream_inf, uri, _height in kept:
        output.extend([stream_inf, uri])
    output.extend(suffix)
    return output


def rewrite_hls_playlist(playlist_name: str, body: str, *, max_height: int | None = None) -> str:
    """Réécrit les URI d'un manifeste vers des URL signées KalanPro.

    Lorsque ``max_height`` est présent dans le jeton du master, les variantes supérieures
    sont retirées avant réécriture. La même politique est propagée aux jetons enfants.
    """
    source_lines = _filter_master_by_height(body.splitlines(), _normalize_max_height(max_height))
    output: list[str] = []
    for original_line in source_lines:
        line = original_line.strip()
        if not line:
            output.append(original_line)
            continue
        if line.startswith("#"):
            def replace_uri(match: re.Match[str]) -> str:
                target = resolve_hls_reference(playlist_name, match.group(1))
                return f'URI="{sign_hls_path(target, max_height=max_height)}"'
            output.append(_URI_ATTR_RE.sub(replace_uri, original_line))
            continue
        target = resolve_hls_reference(playlist_name, line)
        output.append(sign_hls_path(target, max_height=max_height))
    return "\n".join(output) + "\n"
