from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from ._postgres import postgres_connection_env


class Command(BaseCommand):
    help = "Restaure une sauvegarde PostgreSQL custom créée par backup_database."

    def add_arguments(self, parser):
        parser.add_argument("input", help="Fichier .dump à restaurer.")
        parser.add_argument("--confirm", action="store_true", help="Confirmation obligatoire de l'écrasement logique.")

    def handle(self, *args, **options):
        if not options["confirm"]:
            raise CommandError("Ajoutez --confirm pour autoriser la restauration.")
        pg_restore = shutil.which("pg_restore")
        if not pg_restore:
            raise CommandError("pg_restore introuvable. Installez postgresql-client.")
        source = Path(options["input"]).expanduser().resolve()
        if not source.is_file() or source.stat().st_size == 0:
            raise CommandError("Fichier de sauvegarde introuvable ou vide.")
        env, db_args = postgres_connection_env()
        command = [
            pg_restore, *db_args, "--clean", "--if-exists", "--no-owner", "--no-privileges", str(source)
        ]
        result = subprocess.run(command, env=env, text=True, capture_output=True, check=False)
        if result.returncode != 0:
            raise CommandError(result.stderr.strip() or "pg_restore a échoué.")
        self.stdout.write(self.style.SUCCESS(f"Restauration terminée depuis : {source}"))
