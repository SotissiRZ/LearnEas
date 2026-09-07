#!/usr/bin/env bash
set -euo pipefail

PORT_VALUE="${PORT:-8000}"
case "$PORT_VALUE" in
  ''|*[!0-9]*)
    echo "PORT doit être un entier positif (reçu: ${PORT_VALUE:-<vide>})." >&2
    exit 1
    ;;
esac
if [ "$PORT_VALUE" -lt 1 ] || [ "$PORT_VALUE" -gt 65535 ]; then
  echo "PORT hors plage TCP: $PORT_VALUE" >&2
  exit 1
fi

CLOSE_TIMEOUT="${DAPHNE_APPLICATION_CLOSE_TIMEOUT:-10}"
case "$CLOSE_TIMEOUT" in
  ''|*[!0-9]*)
    echo "DAPHNE_APPLICATION_CLOSE_TIMEOUT doit être un entier positif." >&2
    exit 1
    ;;
esac

exec daphne \
  -b 0.0.0.0 \
  -p "$PORT_VALUE" \
  --application-close-timeout "$CLOSE_TIMEOUT" \
  learneas.asgi:application
