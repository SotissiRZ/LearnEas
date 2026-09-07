from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError

from ._postgres import postgres_connection_env


class Command(BaseCommand):
    help = "Restaure une sauvegarde PostgreSQL custom locale ou depuis le stockage privé KalanPro."

    def add_arguments(self, parser):
        parser.add_argument("input", nargs="?", default="", help="Fichier .dump local à restaurer.")
        parser.add_argument("--storage-key", default="", help="Clé privée backups/database/... à restaurer.")
        parser.add_argument("--confirm", action="store_true", help="Confirmation obligatoire de l'écrasement logique.")

    def handle(self, *args, **options):
        if not options["confirm"]:
            raise CommandError("Ajoutez --confirm pour autoriser la restauration.")
        if bool(options["input"]) == bool(options["storage_key"]):
            raise CommandError("Fournissez soit un fichier local, soit --storage-key, mais pas les deux.")

        pg_restore = shutil.which("pg_restore")
        if not pg_restore:
            raise CommandError("pg_restore introuvable. Installez postgresql-client.")

        temporary_path: Path | None = None
        if options["storage_key"]:
            key = str(options["storage_key"]).strip()
            if not key.startswith("backups/database/"):
                raise CommandError("--storage-key doit rester sous backups/database/.")
            try:
                if not default_storage.exists(key):
                    raise CommandError("Sauvegarde privée introuvable.")
                handle = tempfile.NamedTemporaryFile(prefix="kalanpro-restore-", suffix=".dump", delete=False)
                temporary_path = Path(handle.name)
                with handle, default_storage.open(key, "rb") as source:
                    shutil.copyfileobj(source, handle)
                source_path = temporary_path
            except CommandError:
                if temporary_path:
                    temporary_path.unlink(missing_ok=True)
                raise
            except Exception as exc:
                if temporary_path:
                    temporary_path.unlink(missing_ok=True)
                raise CommandError(f"Téléchargement de sauvegarde impossible : {exc.__class__.__name__}") from exc
        else:
            source_path = Path(options["input"]).expanduser().resolve()

        try:
            if not source_path.is_file() or source_path.stat().st_size == 0:
                raise CommandError("Fichier de sauvegarde introuvable ou vide.")
            env, db_args = postgres_connection_env()
            command = [
                pg_restore, *db_args, "--clean", "--if-exists", "--no-owner", "--no-privileges", str(source_path)
            ]
            result = subprocess.run(command, env=env, text=True, capture_output=True, check=False)
            if result.returncode != 0:
                raise CommandError(result.stderr.strip() or "pg_restore a échoué.")
            self.stdout.write(self.style.SUCCESS(f"Restauration terminée depuis : {options['storage_key'] or source_path}"))
        finally:
            if temporary_path:
                temporary_path.unlink(missing_ok=True)
