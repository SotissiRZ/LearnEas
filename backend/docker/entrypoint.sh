#!/usr/bin/env bash
set -euo pipefail

echo "== LearnEas backend entrypoint =="

# --- Attente de la base de données (Postgres) ---
if [ -n "${DB_HOST:-}" ] || [ -n "${DATABASE_URL:-}" ]; then
  echo "Attente de la disponibilité de la base de données..."
  python << 'PYEOF'
import os
import sys
import time

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "learneas.settings")
django.setup()

from django.db import connections
from django.db.utils import OperationalError

max_attempts = 30
for attempt in range(1, max_attempts + 1):
    try:
        connections["default"].cursor()
        print("Base de données disponible.")
        break
    except OperationalError:
        print(f"  ... base de données indisponible (essai {attempt}/{max_attempts}), nouvelle tentative dans 2s")
        time.sleep(2)
else:
    print("Impossible de joindre la base de données, arrêt.", file=sys.stderr)
    sys.exit(1)
PYEOF
fi

echo "Application des migrations..."
python manage.py migrate --noinput

echo "Collecte des fichiers statiques..."
python manage.py collectstatic --noinput --clear

# Crée automatiquement un compte admin si SEED_DEMO=true (pratique en dev/démo, jamais en prod)
if [ "${SEED_DEMO:-false}" = "true" ]; then
  echo "Insertion des données de démonstration (SEED_DEMO=true)..."
  python manage.py seed_demo || echo "seed_demo déjà exécuté ou en erreur non bloquante."
fi

echo "Démarrage : $*"
exec "$@"
