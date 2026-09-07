# KalanPro — Fiche opérationnelle rapide

## Docker dev

```bash
docker compose -f docker-compose.dev.yml up -d --build
docker compose -f docker-compose.dev.yml ps
docker compose -f docker-compose.dev.yml down
```

**Jamais `down -v` sur une instance avec données utiles.**

## Tests backend

```bash
docker compose -f docker-compose.dev.yml exec backend python manage.py check
docker compose -f docker-compose.dev.yml exec backend python manage.py makemigrations --check --dry-run
docker compose -f docker-compose.dev.yml exec backend python manage.py test apps.common apps.payments apps.accounts apps.formations
```

## Tests frontend

```bash
docker compose -f docker-compose.dev.yml exec frontend npm run test:ci
docker compose -f docker-compose.dev.yml exec frontend npm run build:check
docker compose -f docker-compose.dev.yml exec frontend npm run release:qualify:dev
```

## Production gates

```bash
python manage.py production_preflight --json
python manage.py release_gate --strict-infra --deploy --production --json
```

## Post-déploiement

```bash
RELEASE_BASE_URL=https://<frontend> \
RELEASE_BACKEND_URL=https://<backend> \
npm run release:smoke:prod
```

## Sauvegarde

```bash
python manage.py backup_database --upload --delete-local-after-upload
```

## Restauration

```bash
python manage.py restore_database --storage-key backups/database/<dump>.dump --confirm
```

## Paiements

```bash
python manage.py reconcile_payments
```

## Premium

```bash
python manage.py premium_revenue_report --json
```

## Live

```bash
python manage.py rtc_capacity_report --json
```

## Health

```text
Frontend : /healthz
Backend live : /api/health/live/
Backend ready : /api/health/ready/
Admin ops : /api/ops/health/
```

## Logs Docker

```bash
docker compose -f docker-compose.dev.yml logs -f backend
docker compose -f docker-compose.dev.yml logs -f celery_worker
docker compose -f docker-compose.dev.yml logs -f celery_media_worker
docker compose -f docker-compose.dev.yml logs -f celery_beat
docker compose -f docker-compose.dev.yml logs -f frontend
```
