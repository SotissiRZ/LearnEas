from __future__ import annotations

from urllib.parse import quote

from django.conf import settings
from storages.backends.s3 import S3Storage


class KalanProS3Storage(S3Storage):
    """Stockage S3/R2 unique avec politique public/privé par préfixe.

    Les objets restent privés dans le bucket. Lorsqu'un CDN public/origin-access est
    configuré via ``PUBLIC_MEDIA_BASE_URL``, seuls les chemins explicitement classés
    publics reçoivent une URL CDN non signée. Les documents sensibles, vidéos sources,
    HLS, CV et justificatifs continuent d'utiliser des URLs présignées.
    """

    def _public_prefixes(self) -> tuple[str, ...]:
        prefixes = getattr(settings, "MEDIA_PUBLIC_PREFIXES", ()) or ()
        return tuple(str(item).strip().lstrip("/") for item in prefixes if str(item).strip())

    def is_public_name(self, name: str) -> bool:
        clean = str(name or "").lstrip("/")
        return any(clean.startswith(prefix) for prefix in self._public_prefixes())

    def get_object_parameters(self, name):
        params = dict(super().get_object_parameters(name) or {})
        if self.is_public_name(name):
            max_age = max(60, int(getattr(settings, "MEDIA_PUBLIC_CACHE_SECONDS", 31_536_000)))
            params["CacheControl"] = f"public, max-age={max_age}, immutable"
        else:
            params["CacheControl"] = str(
                getattr(settings, "MEDIA_PRIVATE_CACHE_CONTROL", "private, no-store")
            )
        return params

    def url(self, name, parameters=None, expire=None, http_method=None):
        public_base = str(getattr(settings, "PUBLIC_MEDIA_BASE_URL", "") or "").strip().rstrip("/")
        clean_name = str(name or "").lstrip("/")
        if public_base and self.is_public_name(clean_name):
            return f"{public_base}/{quote(clean_name, safe='/')}"

        # Ne jamais déléguer une URL privée à ``custom_domain`` : selon la configuration
        # django-storages/CDN, elle pourrait devenir non signée. Une URL publique n'est
        # permise que par PUBLIC_MEDIA_BASE_URL + préfixe explicitement public.
        params = {"Bucket": self.bucket_name, "Key": clean_name}
        if parameters:
            params.update(parameters)
        ttl = int(expire or getattr(self, "querystring_expire", 300) or 300)
        kwargs = {
            "ClientMethod": "get_object",
            "Params": params,
            "ExpiresIn": ttl,
        }
        if http_method:
            kwargs["HttpMethod"] = http_method
        return self.connection.meta.client.generate_presigned_url(**kwargs)
