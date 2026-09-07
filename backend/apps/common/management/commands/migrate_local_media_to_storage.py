from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Copie les médias d'un ancien MEDIA_ROOT local vers le stockage distant actif sans supprimer la source."

    def add_arguments(self, parser):
        parser.add_argument("--source", default=str(settings.MEDIA_ROOT))
        parser.add_argument("--prefix", default="")
        parser.add_argument("--limit", type=int, default=0)
        parser.add_argument("--apply", action="store_true", help="Effectue réellement les copies. Sans ce flag: dry-run.")

    def handle(self, *args, **options):
        if not getattr(settings, "USE_S3", False):
            raise CommandError("USE_S3=True est requis : la cible doit être le stockage distant configuré.")

        source = Path(options["source"]).expanduser().resolve()
        if not source.is_dir():
            raise CommandError(f"Répertoire source introuvable: {source}")
        prefix = str(options.get("prefix") or "").strip().strip("/")
        limit = max(0, int(options.get("limit") or 0))
        apply_changes = bool(options.get("apply"))

        scanned = copied = skipped = failed = 0
        for path in sorted(source.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(source).as_posix()
            if prefix and not relative.startswith(prefix.rstrip("/") + "/") and relative != prefix:
                continue
            scanned += 1
            if limit and scanned > limit:
                break
            try:
                if default_storage.exists(relative):
                    skipped += 1
                    continue
                if apply_changes:
                    with path.open("rb") as handle:
                        saved = default_storage.save(relative, File(handle, name=path.name))
                    if saved != relative:
                        raise RuntimeError(f"clé modifiée par le stockage: {saved}")
                    copied += 1
                else:
                    self.stdout.write(f"DRY-RUN copy {relative}")
                    copied += 1
            except Exception as exc:
                failed += 1
                self.stderr.write(f"ERROR {relative}: {exc}")

        mode = "APPLY" if apply_changes else "DRY-RUN"
        self.stdout.write(self.style.SUCCESS(
            f"{mode} media migration: scanned={scanned} copy_candidates={copied} skipped={skipped} failed={failed}"
        ))
        if failed:
            raise CommandError(f"Migration incomplète: {failed} fichier(s) en erreur.")
