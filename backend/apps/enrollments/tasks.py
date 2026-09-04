from celery import shared_task
from django.db import transaction
from django.utils import timezone

from .models import Certificate, CertificateEvent


@shared_task
def expire_certificates():
    """Matérialise l'expiration dans le registre sans dépendre d'une consultation publique."""
    now = timezone.now()
    ids = list(
        Certificate.objects.filter(
            status=Certificate.Status.ACTIVE,
            expires_at__isnull=False,
            expires_at__lte=now,
        ).values_list("id", flat=True)
    )
    expired = 0
    for certificate_id in ids:
        with transaction.atomic():
            certificate = Certificate.objects.select_for_update().filter(
                id=certificate_id, status=Certificate.Status.ACTIVE
            ).first()
            if not certificate or not certificate.expires_at or certificate.expires_at > timezone.now():
                continue
            certificate.status = Certificate.Status.EXPIRED
            certificate.save(update_fields=["status"])
            CertificateEvent.objects.get_or_create(
                certificate=certificate,
                event_type=CertificateEvent.EventType.EXPIRED,
                defaults={"details": {"automatic": True}},
            )
            expired += 1
    return {"expired": expired}
