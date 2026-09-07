from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError

from apps.common.production import build_production_preflight_snapshot


class Command(BaseCommand):
    help = "Valide le contrat de configuration KalanPro avant un déploiement production."

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true", help="Sortie JSON stable pour CI/Railway.")
        parser.add_argument(
            "--fail-on-warnings",
            action="store_true",
            help="Traite également les avertissements non bloquants comme un échec.",
        )

    def handle(self, *args, **options):
        snapshot = build_production_preflight_snapshot()
        if options["json"]:
            self.stdout.write(json.dumps(snapshot, ensure_ascii=False, sort_keys=True))
        else:
            self.stdout.write(self.style.SUCCESS("KalanPro production preflight"))
            self.stdout.write(f"status={snapshot['status']}")
            self.stdout.write(f"blockers={len(snapshot['blockers'])}")
            self.stdout.write(f"warnings={len(snapshot['warnings'])}")
            for item in snapshot["blockers"]:
                self.stdout.write(f"BLOCKER {item}")
            for item in snapshot["warnings"]:
                self.stdout.write(f"WARNING {item}")

        if snapshot["status"] != "ok":
            raise CommandError("Production preflight failed: " + ", ".join(snapshot["blockers"]))
        if options["fail_on_warnings"] and snapshot["warnings"]:
            raise CommandError("Production preflight warnings: " + ", ".join(snapshot["warnings"]))
