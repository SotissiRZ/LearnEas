from __future__ import annotations

import json
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Q
from django.utils import timezone

from apps.formations.models import FormationAttendance, FormationSession
from apps.formations.quality import session_quality_snapshot
from apps.formations.rtc import rtc_policy


class Command(BaseCommand):
    help = "Rapport de capacité WebRTC mesh et recommandation SFU basée sur les sessions live actives."

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true", dest="as_json")
        parser.add_argument(
            "--fail-on-sfu-recommended",
            action="store_true",
            help="Retourne une erreur si au moins une salle active dépasse le seuil de recommandation SFU.",
        )

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(seconds=45)
        sessions = list(
            FormationSession.objects.filter(started_at__isnull=False, ended_at__isnull=True)
            .select_related("formation")
            .annotate(
                active_participants=Count(
                    "attendance_records__user",
                    filter=Q(
                        attendance_records__left_at__isnull=True,
                        attendance_records__last_seen_at__gte=cutoff,
                    ),
                    distinct=True,
                )
            )
            .order_by("id")[:100]
        )

        rows = []
        recommended = 0
        poor_reports = 0
        for session in sessions:
            policy = rtc_policy(active_participants=session.active_participants)
            quality = session_quality_snapshot(session.id)
            is_recommended = policy["recommended_topology"] == "sfu"
            recommended += int(is_recommended)
            poor = int((quality.get("quality") or {}).get("poor") or 0)
            poor_reports += poor
            rows.append(
                {
                    "session_id": session.id,
                    "formation": session.formation.title,
                    "participants": int(session.active_participants or 0),
                    "mesh_soft_limit": policy["mesh_soft_limit"],
                    "recommended_topology": policy["recommended_topology"],
                    "sfu_configured": policy["sfu_configured"],
                    "quality_reports": int(quality.get("reports") or 0),
                    "poor_quality_reports": poor,
                    "avg_rtt_ms": quality.get("avg_rtt_ms"),
                    "avg_packet_loss_pct": quality.get("avg_packet_loss_pct"),
                }
            )

        payload = {
            "generated_at": timezone.now().isoformat(),
            "active_sessions": len(rows),
            "sfu_recommended_sessions": recommended,
            "poor_quality_reports": poor_reports,
            "sessions": rows,
        }
        if options["as_json"]:
            self.stdout.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        else:
            self.stdout.write(
                f"Sessions actives: {len(rows)} · SFU recommandé: {recommended} · rapports qualité faible: {poor_reports}"
            )
            for row in rows:
                self.stdout.write(
                    f"- #{row['session_id']} {row['formation']} · {row['participants']} participant(s) · "
                    f"{row['recommended_topology']} · RTT {row['avg_rtt_ms'] if row['avg_rtt_ms'] is not None else '—'} ms · "
                    f"perte {row['avg_packet_loss_pct'] if row['avg_packet_loss_pct'] is not None else '—'}%"
                )

        if options["fail_on_sfu_recommended"] and recommended:
            raise CommandError(f"{recommended} session(s) active(s) dépassent le seuil mesh et recommandent un SFU.")
