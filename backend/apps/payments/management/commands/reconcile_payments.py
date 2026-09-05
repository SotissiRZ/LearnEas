import json

from django.core.management.base import BaseCommand

from apps.payments.tasks import flag_stale_pending_payments, reconcile_pending_payments


class Command(BaseCommand):
    help = "Réconcilie les paiements externes en attente et signale les commandes stale."

    def add_arguments(self, parser):
        parser.add_argument(
            "--stale-only", action="store_true",
            help="Ne lance que la détection des paiements en attente trop longtemps.",
        )

    def handle(self, *args, **options):
        payload = {}
        if not options["stale_only"]:
            payload["reconciliation"] = reconcile_pending_payments()
        payload["stale"] = flag_stale_pending_payments()
        self.stdout.write(json.dumps(payload, ensure_ascii=False, default=str, indent=2))
