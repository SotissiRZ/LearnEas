from __future__ import annotations

from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.files.storage import default_storage
from django.utils import timezone


@shared_task
def cleanup_stale_multipart_uploads():
    """Abandonne les multipart vidéo S3/R2 trop anciens.

    La tâche est volontairement bornée pour ne jamais faire d'un nettoyage une opération
    lourde sur un grand bucket. Un lifecycle fournisseur reste recommandé en seconde ligne.
    """
    if not getattr(settings, "USE_S3", False):
        return {"status": "skipped", "reason": "local_storage", "aborted": 0}

    connection = getattr(default_storage, "connection", None)
    if connection is None:
        return {"status": "error", "reason": "storage_connection", "aborted": 0}

    client = connection.meta.client
    bucket = settings.AWS_STORAGE_BUCKET_NAME
    cutoff = timezone.now() - timedelta(hours=max(1, int(settings.MULTIPART_UPLOAD_MAX_AGE_HOURS)))
    limit = max(1, int(settings.MULTIPART_CLEANUP_MAX_ABORTS))
    key_marker = None
    upload_marker = None
    scanned = 0
    aborted = 0

    while aborted < limit:
        kwargs = {"Bucket": bucket, "Prefix": "courses/videos/direct/", "MaxUploads": min(1000, limit)}
        if key_marker:
            kwargs["KeyMarker"] = key_marker
        if upload_marker:
            kwargs["UploadIdMarker"] = upload_marker
        response = client.list_multipart_uploads(**kwargs)
        uploads = response.get("Uploads") or []
        scanned += len(uploads)
        for item in uploads:
            initiated = item.get("Initiated")
            if not initiated or initiated >= cutoff:
                continue
            client.abort_multipart_upload(Bucket=bucket, Key=item["Key"], UploadId=item["UploadId"])
            aborted += 1
            if aborted >= limit:
                break
        if aborted >= limit or not response.get("IsTruncated"):
            break
        key_marker = response.get("NextKeyMarker")
        upload_marker = response.get("NextUploadIdMarker")
        if not key_marker:
            break

    return {"status": "ok", "scanned": scanned, "aborted": aborted, "limit": limit}
