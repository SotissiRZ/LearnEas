from datetime import timedelta
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import ProductEvent


@shared_task
def purge_old_product_events():
    """Supprime uniquement la télémétrie produit au-delà de la rétention configurée.

    Les tables métier (paiements, inscriptions, candidatures, certificats) ne sont jamais touchées.
    """
    days = min(max(int(getattr(settings, "ANALYTICS_RETENTION_DAYS", 395)), 30), 1095)
    cutoff = timezone.now() - timedelta(days=days)
    deleted, _ = ProductEvent.objects.filter(occurred_at__lt=cutoff).delete()
    return {"deleted": deleted, "retention_days": days}
