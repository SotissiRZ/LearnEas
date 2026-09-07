from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError

from apps.common.release import build_release_gate_snapshot


class Command(BaseCommand):
    help = "Qualifie une release KalanPro: checks Django, migrations et dépendances critiques."

    def add_arguments(self, parser):
        parser.add_argument(
            "--strict-infra",
            action="store_true",
            help="Exige aussi broker/workers et stockage. À utiliser en staging/production.",
        )
        parser.add_argument(
            "--deploy",
            action="store_true",
            help="Active les deployment checks Django et traite leurs warnings comme bloquants.",
        )
        parser.add_argument(
            "--production",
            action="store_true",
            help="Ajoute le contrat de configuration production V93 aux blockers du gate.",
        )
        parser.add_argument("--json", action="store_true", help="Sortie JSON stable pour CI.")

    def handle(self, *args, **options):
        snapshot = build_release_gate_snapshot(
            strict_infra=bool(options["strict_infra"]),
            deploy=bool(options["deploy"]),
            production=bool(options["production"]),
        )
        if options["json"]:
            self.stdout.write(json.dumps(snapshot, ensure_ascii=False, sort_keys=True))
        else:
            self.stdout.write(self.style.SUCCESS("KalanPro release gate"))
            self.stdout.write(f"status={snapshot['status']}")
            self.stdout.write(f"pending_migrations={len(snapshot['pending_migrations'])}")
            self.stdout.write(f"django_issues={len(snapshot['django_issues'])}")
            for name, payload in snapshot["services"].items():
                self.stdout.write(f"{name}={payload.get('status', 'error')}")
            if snapshot["blockers"]:
                self.stdout.write("blockers=" + ",".join(snapshot["blockers"]))

        if snapshot["status"] != "ok":
            raise CommandError("Release gate failed: " + ", ".join(snapshot["blockers"]))
