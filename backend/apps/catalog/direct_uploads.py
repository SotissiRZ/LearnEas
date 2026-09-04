from __future__ import annotations

import math
import uuid
from pathlib import Path

from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework import serializers


ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4v"}
VIDEO_CONTENT_TYPES = {
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
}


def direct_multipart_enabled() -> bool:
    return bool(
        getattr(settings, "USE_S3", False)
        and getattr(settings, "DIRECT_MEDIA_UPLOADS_ENABLED", True)
    )


def part_size_bytes() -> int:
    configured_mb = max(5, int(getattr(settings, "DIRECT_UPLOAD_PART_SIZE_MB", 16)))
    return configured_mb * 1024 * 1024


def _max_video_bytes() -> int:
    return int(getattr(settings, "MAX_VIDEO_UPLOAD_MB", 2048)) * 1024 * 1024


def _bucket_name() -> str:
    bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", "")
    if not bucket:
        raise RuntimeError("Bucket S3/R2 non configuré.")
    return bucket


def _s3_client():
    # django-storages réutilise ici exactement les credentials/endpoint configurés pour
    # default_storage, y compris Cloudflare R2 et les autres API S3 compatibles.
    connection = getattr(default_storage, "connection", None)
    if connection is None:
        raise RuntimeError("Le stockage actif ne fournit pas de connexion S3.")
    return connection.meta.client


def validate_source_video(filename: str, size: int) -> tuple[str, str]:
    ext = Path(filename or "").suffix.lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise serializers.ValidationError({
            "filename": "Format vidéo non pris en charge. Utilisez MP4, WebM, MOV ou M4V."
        })
    if size <= 0:
        raise serializers.ValidationError({"size": "Le fichier vidéo est vide."})
    if size > _max_video_bytes():
        raise serializers.ValidationError({
            "size": f"La vidéo dépasse la limite de {getattr(settings, 'MAX_VIDEO_UPLOAD_MB', 2048)} Mo."
        })
    return ext, VIDEO_CONTENT_TYPES[ext]


def user_upload_prefix(user_id: int) -> str:
    return f"courses/videos/direct/{int(user_id)}/"


def validate_user_object_key(user_id: int, object_key: str) -> str:
    key = (object_key or "").strip().lstrip("/")
    if not key.startswith(user_upload_prefix(user_id)) or ".." in key.split("/"):
        raise serializers.ValidationError({"object_key": "Clé d'upload vidéo invalide."})
    if Path(key).suffix.lower() not in ALLOWED_VIDEO_EXTENSIONS:
        raise serializers.ValidationError({"object_key": "Extension d'objet vidéo invalide."})
    return key


def initiate_multipart_upload(*, user_id: int, filename: str, size: int) -> dict:
    if not direct_multipart_enabled():
        raise RuntimeError("Upload direct S3/R2 désactivé.")
    ext, content_type = validate_source_video(filename, size)
    key = f"{user_upload_prefix(user_id)}{uuid.uuid4().hex}{ext}"
    response = _s3_client().create_multipart_upload(
        Bucket=_bucket_name(),
        Key=key,
        ContentType=content_type,
        CacheControl="private, no-store",
    )
    chunk_size = part_size_bytes()
    return {
        "object_key": key,
        "upload_id": response["UploadId"],
        "part_size_bytes": chunk_size,
        "parts_count": math.ceil(size / chunk_size),
        "content_type": content_type,
    }


def presign_upload_part(*, user_id: int, object_key: str, upload_id: str, part_number: int) -> str:
    key = validate_user_object_key(user_id, object_key)
    if not upload_id:
        raise serializers.ValidationError({"upload_id": "Identifiant d'upload manquant."})
    if part_number < 1 or part_number > 10000:
        raise serializers.ValidationError({"part_number": "Numéro de bloc invalide."})
    ttl = max(300, int(getattr(settings, "DIRECT_UPLOAD_URL_TTL_SECONDS", 3600)))
    return _s3_client().generate_presigned_url(
        "upload_part",
        Params={
            "Bucket": _bucket_name(),
            "Key": key,
            "UploadId": upload_id,
            "PartNumber": part_number,
        },
        ExpiresIn=ttl,
        HttpMethod="PUT",
    )


def complete_multipart_upload(
    *, user_id: int, object_key: str, upload_id: str, parts: list[dict], expected_size: int
) -> dict:
    key = validate_user_object_key(user_id, object_key)
    if not upload_id:
        raise serializers.ValidationError({"upload_id": "Identifiant d'upload manquant."})
    if not isinstance(parts, list) or not parts:
        raise serializers.ValidationError({"parts": "Aucun bloc uploadé n'a été fourni."})

    cleaned_parts: list[dict] = []
    previous = 0
    for part in parts:
        try:
            number = int(part["PartNumber"])
            etag = str(part["ETag"]).strip()
        except (KeyError, TypeError, ValueError):
            raise serializers.ValidationError({"parts": "Liste de blocs multipart invalide."})
        if number <= previous or not etag or number < 1 or number > 10000:
            raise serializers.ValidationError({"parts": "Ordre ou ETag multipart invalide."})
        previous = number
        cleaned_parts.append({"PartNumber": number, "ETag": etag})

    client = _s3_client()
    client.complete_multipart_upload(
        Bucket=_bucket_name(),
        Key=key,
        UploadId=upload_id,
        MultipartUpload={"Parts": cleaned_parts},
    )
    head = client.head_object(Bucket=_bucket_name(), Key=key)
    actual_size = int(head.get("ContentLength") or 0)
    max_size = _max_video_bytes()
    if actual_size <= 0 or actual_size > max_size or (expected_size > 0 and actual_size != expected_size):
        try:
            client.delete_object(Bucket=_bucket_name(), Key=key)
        finally:
            raise serializers.ValidationError({
                "video_file": "La taille finale de la vidéo ne correspond pas à l'upload attendu."
            })
    return {"object_key": key, "size": actual_size}


def abort_multipart_upload(*, user_id: int, object_key: str, upload_id: str) -> None:
    key = validate_user_object_key(user_id, object_key)
    if not upload_id:
        return
    _s3_client().abort_multipart_upload(
        Bucket=_bucket_name(),
        Key=key,
        UploadId=upload_id,
    )
