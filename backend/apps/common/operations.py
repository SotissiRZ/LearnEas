from __future__ import annotations

import shutil
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.db import connection
from django.utils import timezone


def _ok(detail=None):
    payload = {"status": "ok"}
    if detail is not None:
        payload["detail"] = detail
    return payload


def _error(exc: Exception):
    return {"status": "error", "detail": str(exc)[:240] or exc.__class__.__name__}


def _database_check():
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return _ok()
    except Exception as exc:
        return _error(exc)


def _cache_check():
    try:
        marker = f"ops:{timezone.now().timestamp()}"
        cache.set(marker, "ok", 10)
        if cache.get(marker) != "ok":
            raise RuntimeError("cache read/write failed")
        cache.delete(marker)
        return _ok()
    except Exception as exc:
        return _error(exc)


def _broker_check():
    queues = {"default": None, "notifications": None, "media": None}
    try:
        import redis

        client = redis.Redis.from_url(
            settings.CELERY_BROKER_URL,
            socket_connect_timeout=1.5,
            socket_timeout=1.5,
            decode_responses=False,
        )
        client.ping()
        for queue in queues:
            queues[queue] = int(client.llen(queue))
        warning_depth = max(1, int(getattr(settings, "OPERATIONS_QUEUE_WARNING_DEPTH", 100)))

        workers = 0
        consumers = {"default": 0, "notifications": 0, "media": 0}
        try:
            from learneas.celery import app as celery_app
            active_queues = celery_app.control.inspect(timeout=0.8).active_queues() or {}
            workers = len(active_queues)
            for worker_queues in active_queues.values():
                names = {str(item.get("name") or "") for item in (worker_queues or [])}
                for queue in consumers:
                    if queue in names:
                        consumers[queue] += 1
        except Exception:
            # Le broker reste testable même si aucun worker ne répond au broadcast.
            workers = 0

        status = "ok"
        if any((value or 0) >= warning_depth for value in queues.values()) or workers == 0:
            status = "warning"
        return {
            "status": status, "queues": queues, "warning_depth": warning_depth,
            "workers": workers, "consumers": consumers,
        }
    except Exception as exc:
        return {"status": "error", "queues": queues, "detail": str(exc)[:240]}


def _s3_client():
    connection_obj = getattr(default_storage, "connection", None)
    if connection_obj is None:
        raise RuntimeError("storage connection unavailable")
    return connection_obj.meta.client


def _scan_s3(client, bucket: str, max_objects: int):
    count = 0
    total_bytes = 0
    token = None
    truncated = False
    while count < max_objects:
        kwargs = {"Bucket": bucket, "MaxKeys": min(1000, max_objects - count)}
        if token:
            kwargs["ContinuationToken"] = token
        response = client.list_objects_v2(**kwargs)
        contents = response.get("Contents") or []
        for item in contents:
            count += 1
            total_bytes += int(item.get("Size") or 0)
            if count >= max_objects:
                break
        if not response.get("IsTruncated") or count >= max_objects:
            truncated = bool(response.get("IsTruncated") and count >= max_objects)
            break
        token = response.get("NextContinuationToken")
        if not token:
            break
    return {
        "objects_scanned": count,
        "bytes_scanned": total_bytes,
        "scan_truncated": truncated,
        "scan_limit": max_objects,
    }


def _multipart_summary(client, bucket: str):
    response = client.list_multipart_uploads(Bucket=bucket, Prefix="courses/videos/direct/", MaxUploads=100)
    uploads = response.get("Uploads") or []
    cutoff = timezone.now() - timedelta(hours=max(1, int(getattr(settings, "MULTIPART_UPLOAD_MAX_AGE_HOURS", 24))))
    stale = 0
    for item in uploads:
        initiated = item.get("Initiated")
        if initiated and initiated < cutoff:
            stale += 1
    return {
        "active": len(uploads),
        "stale": stale,
        "truncated": bool(response.get("IsTruncated")),
    }


def _storage_check(*, scan: bool = False):
    using_s3 = bool(getattr(settings, "USE_S3", False))
    base = {
        "backend": "s3" if using_s3 else "local",
        "remote_required": bool(getattr(settings, "REQUIRE_REMOTE_MEDIA", False)),
        "direct_uploads": bool(getattr(settings, "DIRECT_MEDIA_UPLOADS_ENABLED", False)),
        "public_cdn": bool(getattr(settings, "PUBLIC_MEDIA_BASE_URL", "")),
    }
    try:
        if using_s3:
            bucket = str(getattr(settings, "AWS_STORAGE_BUCKET_NAME", "") or "")
            client = _s3_client()
            client.head_bucket(Bucket=bucket)
            base["bucket"] = bucket
            base["multipart"] = _multipart_summary(client, bucket)
            if scan:
                max_objects = max(1, int(getattr(settings, "OPERATIONS_STORAGE_SCAN_MAX_OBJECTS", 2000)))
                base["usage"] = _scan_s3(client, bucket, max_objects)
        else:
            root = Path(settings.MEDIA_ROOT)
            target = root if root.exists() else Path(settings.BASE_DIR)
            usage = shutil.disk_usage(target)
            base["path"] = str(root)
            base["usage"] = {
                "total_bytes": int(usage.total),
                "used_bytes": int(usage.used),
                "free_bytes": int(usage.free),
                "used_percent": round((usage.used / usage.total) * 100, 1) if usage.total else 0,
            }
        base["status"] = "ok"
    except Exception as exc:
        base["status"] = "error"
        base["detail"] = str(exc)[:240]
    return base


def _domain_metrics():
    from apps.catalog.models import Lesson, StreamingStatus
    from apps.notifications.models import EmailDelivery, WhatsAppDelivery
    from apps.payments.models import PaymentGateway, PaymentIssue
    from apps.support.models import ModerationReport, SupportTicket
    from apps.formations.models import FormationAttendance, FormationSession
    from apps.formations.quality import session_quality_snapshot

    now = timezone.now()
    last_24h = now - timedelta(hours=24)
    live_cutoff = now - timedelta(minutes=2)
    active_live_ids = list(FormationSession.objects.filter(
        started_at__isnull=False, ended_at__isnull=True
    ).values_list("id", flat=True)[:50])
    quality_reports = 0
    poor_quality_reports = 0
    rtt_values = []
    packet_loss_values = []
    for session_id in active_live_ids:
        quality = session_quality_snapshot(session_id)
        quality_reports += int(quality.get("reports") or 0)
        poor_quality_reports += int((quality.get("quality") or {}).get("poor") or 0)
        if quality.get("avg_rtt_ms") is not None:
            rtt_values.append(float(quality["avg_rtt_ms"]))
        if quality.get("avg_packet_loss_pct") is not None:
            packet_loss_values.append(float(quality["avg_packet_loss_pct"]))
    return {
        "streaming": {
            "pending": Lesson.objects.filter(streaming_status=StreamingStatus.PENDING).count(),
            "processing": Lesson.objects.filter(streaming_status=StreamingStatus.PROCESSING).count(),
            "ready": Lesson.objects.filter(streaming_status=StreamingStatus.READY).count(),
            "failed": Lesson.objects.filter(streaming_status=StreamingStatus.FAILED).count(),
        },
        "finance": {
            "open_issues": PaymentIssue.objects.filter(status=PaymentIssue.Status.OPEN).count(),
            "critical_issues": PaymentIssue.objects.filter(
                status=PaymentIssue.Status.OPEN, severity=PaymentIssue.Severity.CRITICAL
            ).count(),
            "active_gateways": PaymentGateway.objects.filter(is_active=True).count(),
        },
        "support": {
            "open": SupportTicket.objects.filter(status=SupportTicket.Status.OPEN).count(),
            "in_progress": SupportTicket.objects.filter(status=SupportTicket.Status.IN_PROGRESS).count(),
            "urgent": SupportTicket.objects.filter(
                status__in=[SupportTicket.Status.OPEN, SupportTicket.Status.IN_PROGRESS],
                priority=SupportTicket.Priority.URGENT,
            ).count(),
            "moderation_pending": ModerationReport.objects.filter(
                status__in=[ModerationReport.Status.PENDING, ModerationReport.Status.REVIEWING]
            ).count(),
        },
        "notifications": {
            "email_failed_24h": EmailDelivery.objects.filter(
                status=EmailDelivery.Status.FAILED, created_at__gte=last_24h
            ).count(),
            "whatsapp_failed_24h": WhatsAppDelivery.objects.filter(
                status=WhatsAppDelivery.Status.FAILED, created_at__gte=last_24h
            ).count(),
        },
        "live": {
            "active_sessions": FormationSession.objects.filter(
                started_at__isnull=False, ended_at__isnull=True
            ).count(),
            "recent_participants": FormationAttendance.objects.filter(
                left_at__isnull=True, last_seen_at__gte=live_cutoff
            ).count(),
            "quality_reports": quality_reports,
            "poor_quality_reports": poor_quality_reports,
            "avg_rtt_ms": round(sum(rtt_values) / len(rtt_values), 1) if rtt_values else None,
            "avg_packet_loss_pct": round(sum(packet_loss_values) / len(packet_loss_values), 2) if packet_loss_values else None,
        },
    }


def _provider_config():
    return {
        "resend": {
            "enabled": bool(getattr(settings, "RESEND_ENABLED", False)),
            "dry_run": bool(getattr(settings, "RESEND_DRY_RUN", False)),
        },
        "whatsapp": {
            "enabled": bool(getattr(settings, "WHATSAPP_ENABLED", False)),
            "dry_run": bool(getattr(settings, "WHATSAPP_DRY_RUN", False)),
        },
        "ai": {
            "configured": bool(getattr(settings, "AI_API_KEY", "")),
            "dry_run": bool(getattr(settings, "AI_DRY_RUN", False)),
        },
        "turn": {
            "configured": bool(getattr(settings, "RTC_TURN_SECRET", "") or getattr(settings, "RTC_TURN_CREDENTIAL", "")),
            "multi_url": bool(str(getattr(settings, "RTC_TURN_URLS", "") or "").strip()),
            "ice_transport_policy": str(getattr(settings, "RTC_ICE_TRANSPORT_POLICY", "all") or "all"),
        },
        "sfu": {
            "configured": bool(str(getattr(settings, "RTC_SFU_URL", "") or "").strip()),
            "recommend_threshold": max(int(getattr(settings, "RTC_SFU_RECOMMEND_THRESHOLD", 7)), 3),
            "active_adapter": False,
        },
    }


def build_operations_snapshot(*, scan_storage: bool = False):
    services = {
        "database": _database_check(),
        "cache": _cache_check(),
        "broker": _broker_check(),
        "storage": _storage_check(scan=scan_storage),
    }
    statuses = [item.get("status") for item in services.values()]
    overall = "error" if "error" in statuses else ("warning" if "warning" in statuses else "ok")
    return {
        "status": overall,
        "generated_at": timezone.now().isoformat(),
        "environment": {
            "debug": bool(settings.DEBUG),
            "remote_media": bool(getattr(settings, "USE_S3", False)),
            "hls_enabled": bool(getattr(settings, "HLS_STREAMING_ENABLED", False)),
        },
        "services": services,
        "metrics": _domain_metrics(),
        "providers": _provider_config(),
    }
