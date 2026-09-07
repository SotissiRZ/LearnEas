#!/usr/bin/env bash
set -euo pipefail

echo "== KalanPro backend entrypoint =="

# Garde-fou indépendant de Django : aucune donnée de démonstration en production.
case "${DEBUG:-True}" in
  False|false|0|no|NO)
    case "${SEED_DEMO:-false}" in
      True|true|1|yes|YES) echo "SEED_DEMO=true interdit avec DEBUG=false." >&2; exit 1 ;;
    esac
  ;;
esac


if [ "${SKIP_BOOTSTRAP:-false}" != "true" ]; then
  # --- Attente de la base de données (PostgreSQL) ---
  # Le test est volontairement effectué directement avec psycopg2 plutôt qu'après
  # django.setup(). Cela évite qu'un import/app hook Django masque la vraie cause
  # d'un échec de connexion et fournit un diagnostic exploitable dans Docker.
  if [ -n "${DB_HOST:-}" ] || [ -n "${DATABASE_URL:-}" ]; then
    echo "Attente de la disponibilité de la base de données..."
    python <<'PYEOF'
import os
import sys
import time
from urllib.parse import urlsplit, urlunsplit

import psycopg2
from psycopg2 import OperationalError

max_attempts = int(os.getenv("DB_WAIT_MAX_ATTEMPTS", "30"))
delay_seconds = float(os.getenv("DB_WAIT_DELAY_SECONDS", "2"))
connect_timeout = int(os.getenv("DB_CONNECT_TIMEOUT_SECONDS", "3"))
database_url = os.getenv("DATABASE_URL", "").strip()


def masked_url(value: str) -> str:
    if not value:
        return ""
    try:
        parts = urlsplit(value)
        host = parts.hostname or ""
        port = f":{parts.port}" if parts.port else ""
        username = parts.username or ""
        auth = f"{username}:***@" if username else ""
        netloc = f"{auth}{host}{port}"
        return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
    except Exception:
        return "<DATABASE_URL configurée>"


def connect():
    if database_url:
        # psycopg2/libpq accepte l'URI PostgreSQL directement. connect_timeout borne
        # chaque essai afin d'éviter un démarrage Docker bloqué trop longtemps.
        return psycopg2.connect(database_url, connect_timeout=connect_timeout)

    return psycopg2.connect(
        dbname=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        connect_timeout=connect_timeout,
    )

if database_url:
    print(f"Cible PostgreSQL : {masked_url(database_url)}", flush=True)
else:
    print(
        "Cible PostgreSQL : "
        f"{os.getenv('DB_USER', 'postgres')}@{os.getenv('DB_HOST', 'localhost')}:"
        f"{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'postgres')}",
        flush=True,
    )

for attempt in range(1, max_attempts + 1):
    conn = None
    try:
        conn = connect()
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        print("Base de données disponible.", flush=True)
        break
    except OperationalError as exc:
        print(
            f"  ... PostgreSQL indisponible (essai {attempt}/{max_attempts}) : {exc}",
            file=sys.stderr,
            flush=True,
        )
        if attempt < max_attempts:
            time.sleep(delay_seconds)
    finally:
        if conn is not None:
            conn.close()
else:
    print("Impossible de joindre PostgreSQL, arrêt.", file=sys.stderr, flush=True)
    sys.exit(1)
PYEOF
  fi

  if [ "${RUN_MIGRATIONS_ON_BOOT:-true}" = "true" ]; then
    echo "Application des migrations..."
    python manage.py migrate --noinput
  else
    echo "Migrations au démarrage désactivées (RUN_MIGRATIONS_ON_BOOT=false)."
  fi

  if [ "${COLLECTSTATIC_ON_BOOT:-true}" = "true" ]; then
    echo "Collecte des fichiers statiques..."
    python manage.py collectstatic --noinput --clear
  else
    echo "Collectstatic au démarrage désactivé (COLLECTSTATIC_ON_BOOT=false)."
  fi

  # Crée automatiquement les comptes de démonstration si SEED_DEMO=true.
  # Cette option reste réservée au développement/démo et doit rester désactivée en prod.
  if [ "${SEED_DEMO:-false}" = "true" ]; then
    echo "Insertion des données de démonstration (SEED_DEMO=true)..."
    python manage.py seed_demo || echo "seed_demo déjà exécuté ou en erreur non bloquante."
  fi

  if [ "${AI_REBUILD_INDEX_ON_BOOT:-false}" = "true" ]; then
    echo "Reconstruction de l’index KalanPro AI..."
    python manage.py rebuild_ai_index --quiet --if-empty || echo "Index IA indisponible, démarrage non bloqué."
  fi
fi

# Les volumes existants peuvent avoir été créés par une ancienne image root.
# Le chown au démarrage préserve la compatibilité puis le processus applicatif perd ses privilèges.
if [ "$(id -u)" = "0" ]; then
  chown -R learneas:learneas /app/staticfiles /app/media 2>/dev/null || true
  echo "Démarrage en utilisateur non privilégié learneas : $*"
  exec gosu learneas "$@"
fi

echo "Démarrage : $*"
exec "$@"
