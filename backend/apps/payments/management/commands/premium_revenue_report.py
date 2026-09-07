import json
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Sum
from django.utils import timezone

from apps.accounts.models import PlatformSettings
from apps.payments.models import (
    InstructorLedgerEntry,
    LearnerSubscription,
    PremiumRenewalProfile,
    PremiumRevenueAllocation,
)


class Command(BaseCommand):
    help = "Résumé opérationnel V92 du cycle Premium et de la redistribution créateurs."

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true", dest="as_json")
        parser.add_argument(
            "--fail-on-past-due",
            action="store_true",
            help="Retourne un code d'échec s'il existe des renouvellements Premium échus.",
        )

    def handle(self, *args, **options):
        now = timezone.now()
        config = PlatformSettings.load()
        premium_net = InstructorLedgerEntry.objects.filter(
            entry_type__in=[
                InstructorLedgerEntry.EntryType.PREMIUM,
                InstructorLedgerEntry.EntryType.PREMIUM_REFUND,
            ]
        ).aggregate(v=Sum("amount"))["v"] or Decimal("0")
        payload = {
            "generated_at": now.isoformat(),
            "creator_pool_percent": int(config.learner_premium_creator_pool_percent),
            "renewals": {
                "scheduled": PremiumRenewalProfile.objects.filter(
                    enabled=True, status=PremiumRenewalProfile.Status.SCHEDULED
                ).count(),
                "action_required": PremiumRenewalProfile.objects.filter(
                    enabled=True, status=PremiumRenewalProfile.Status.ACTION_REQUIRED
                ).count(),
                "past_due": PremiumRenewalProfile.objects.filter(
                    enabled=True, status=PremiumRenewalProfile.Status.PAST_DUE
                ).count(),
                "paused": PremiumRenewalProfile.objects.filter(
                    enabled=True, status=PremiumRenewalProfile.Status.PAUSED
                ).count(),
            },
            "revenue": {
                "unsettled_periods": LearnerSubscription.all_objects.filter(
                    ends_at__lte=now, revenue_settled_at__isnull=True
                ).count(),
                "settled_periods": LearnerSubscription.all_objects.filter(
                    revenue_settled_at__isnull=False
                ).count(),
                "active_allocations": PremiumRevenueAllocation.objects.filter(
                    reversed_at__isnull=True
                ).count(),
                "reversed_allocations": PremiumRevenueAllocation.objects.filter(
                    reversed_at__isnull=False
                ).count(),
                "creator_ledger_net_eur": str(premium_net.quantize(Decimal("0.01"))),
            },
            "automatic_charge": False,
        }
        if options["as_json"]:
            self.stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        else:
            self.stdout.write(f"Pool créateurs: {payload['creator_pool_percent']}%")
            self.stdout.write(
                "Renouvellements: "
                f"{payload['renewals']['scheduled']} planifié(s), "
                f"{payload['renewals']['action_required']} à confirmer, "
                f"{payload['renewals']['past_due']} échu(s), "
                f"{payload['renewals']['paused']} en pause"
            )
            self.stdout.write(
                "Redistribution: "
                f"{payload['revenue']['unsettled_periods']} période(s) à répartir, "
                f"{payload['revenue']['active_allocations']} allocation(s) active(s), "
                f"net créateurs {payload['revenue']['creator_ledger_net_eur']} EUR"
            )
        if options["fail_on_past_due"] and payload["renewals"]["past_due"]:
            raise SystemExit(2)
