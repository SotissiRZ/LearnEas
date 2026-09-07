from __future__ import annotations

import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.core.files import File

from ._postgres import postgres_connection_env


class Command(BaseCommand):
    help = "Crée une sauvegarde PostgreSQL au format custom (pg_dump), avec upload privé optionnel."

    def add_arguments(self, parser):
        parser.add_argument("--output", default="", help="Chemin du fichier .dump à créer.")
        parser.add_argument(
            "--upload",
            action="store_true",
            help="Envoie ensuite la sauvegarde dans le stockage privé KalanPro sous backups/database/.",
        )
        parser.add_argument(
            "--delete-local-after-upload",
            action="store_true",
            help="Supprime la copie locale uniquement après un upload réussi.",
        )

    def handle(self, *args, **options):
        pg_dump = shutil.which("pg_dump")
        if not pg_dump:
            raise CommandError("pg_dump introuvable. Installez postgresql-client.")
        default_name = f"kalanpro-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.dump"
        output = Path(options["output"] or Path("backups") / default_name).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        env, db_args = postgres_connection_env()
        command = [pg_dump, *db_args, "--format=custom", "--no-owner", "--no-privileges", "--file", str(output)]
        result = subprocess.run(command, env=env, text=True, capture_output=True, check=False)
        if result.returncode != 0:
            output.unlink(missing_ok=True)
            raise CommandError(result.stderr.strip() or "pg_dump a échoué.")
        if not output.is_file() or output.stat().st_size == 0:
            raise CommandError("La sauvegarde produite est vide.")

        self.stdout.write(self.style.SUCCESS(f"Sauvegarde créée : {output} ({output.stat().st_size} octets)"))

        if options["upload"]:
            storage_key = f"backups/database/{output.name}"
            try:
                if default_storage.exists(storage_key):
                    raise CommandError(f"La clé de sauvegarde existe déjà : {storage_key}")
                with output.open("rb") as stream:
                    saved_key = default_storage.save(storage_key, File(stream, name=output.name))
            except CommandError:
                raise
            except Exception as exc:
                raise CommandError(f"Upload de sauvegarde impossible : {exc.__class__.__name__}") from exc
            self.stdout.write(self.style.SUCCESS(f"Sauvegarde privée envoyée : {saved_key}"))
            if options["delete_local_after_upload"]:
                output.unlink(missing_ok=True)
                self.stdout.write("Copie locale supprimée après upload réussi.")
