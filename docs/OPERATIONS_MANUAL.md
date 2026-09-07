# KalanPro — Manuel d’exploitation, maintenance et déploiement

**Version de référence : V93.4**  
**Stack : Django 5 / DRF / Channels / Daphne, PostgreSQL, Redis, Celery, Next.js 15, S3/R2, Railway + Vercel**

Ce document est le point d’entrée opérationnel de KalanPro. Il complète les documents techniques par version (`V79` à `V93`) et doit être utilisé pour l’exploitation quotidienne, la maintenance, les releases et les incidents.

## 1. Règles d’or

1. **Ne jamais exécuter `docker compose down -v` en environnement contenant des données utiles.** Le `-v` supprime les volumes PostgreSQL, Redis et médias locaux.
2. **Ne jamais utiliser `make clean` sur une instance contenant des données utiles** : cette cible exécute `docker compose down -v`.
3. Une release n’est promue qu’après : backend vert, frontend vert, build vert, gate de release vert, smoke post-déploiement vert.
4. Les migrations de production passent par le **Pre-deploy Railway**, pas par tous les workers.
5. Un seul `celery-beat` doit être actif par environnement.
6. Le bucket S3/R2 de production reste privé. Les médias publics passent uniquement par les préfixes explicitement autorisés et `PUBLIC_MEDIA_BASE_URL`.
7. Les écritures de paiement, d’audit et de redistribution Premium ne sont jamais supprimées pour « réparer » un incident : utiliser les écritures correctives prévues.
8. Les variables `NEXT_PUBLIC_*` sont publiques côté navigateur. Aucun secret, token, mot de passe ou clé privée ne doit porter ce préfixe.
9. Staging doit précéder production pour chaque changement de code, migration, fournisseur ou infrastructure.
10. Après toute modification de variables Vercel `NEXT_PUBLIC_*`, **rebuild/redeploy obligatoire**.

## 2. Architecture runtime

```text
Utilisateur
   |
   v
Vercel / Next.js
   |  /api/* rewrite same-origin
   v
Railway backend Django/DRF/Channels/Daphne
   |\
   | +--> PostgreSQL
   | +--> Redis (cache, Channels, broker Celery)
   | +--> S3/R2 (médias privés + HLS + sauvegardes)
   | +--> Paiements / Resend / WhatsApp / IA / TURN
   |
   +--> celery-worker (default,notifications)
   +--> celery-media (media)
   +--> celery-beat (planification)
```

### Services Railway recommandés

| Service | Public | Rôle | Commande |
|---|---:|---|---|
| `backend` | oui | API, admin, WebSocket | image Docker, `/app/docker/start-web.sh` |
| `celery-worker` | non | tâches générales + notifications | `celery -A learneas worker --loglevel=info -Q default,notifications` |
| `celery-media` | non | vidéo/HLS | `celery -A learneas worker --loglevel=info -Q media --concurrency=1 --prefetch-multiplier=1` |
| `celery-beat` | non | tâches périodiques | `celery -A learneas beat --loglevel=info` |
| PostgreSQL | non | données métier | service managé |
| Redis | non | cache, Channels, Celery | service managé |
| ClamAV | non | scan fichiers | requis si `PRODUCTION_REQUIRE_MALWARE_SCAN=True` |
| TURN/coturn | public UDP/TCP/TLS | WebRTC | service dédié/externe recommandé |

## 3. Documentation associée

- [`DEPLOYMENT_RAILWAY_VERCEL.md`](./DEPLOYMENT_RAILWAY_VERCEL.md) — procédure staging/prod.
- [`ENVIRONMENT_VARIABLES.md`](./ENVIRONMENT_VARIABLES.md) — variables et secrets.
- [`MAINTENANCE_RUNBOOK.md`](./MAINTENANCE_RUNBOOK.md) — exploitation quotidienne.
- [`BACKUP_RESTORE_DISASTER_RECOVERY.md`](./BACKUP_RESTORE_DISASTER_RECOVERY.md) — sauvegarde, restauration, PRA.
- [`INCIDENT_RESPONSE.md`](./INCIDENT_RESPONSE.md) — incidents P0–P3.
- [`PERFORMANCE_TROUBLESHOOTING.md`](./PERFORMANCE_TROUBLESHOOTING.md) — lenteur, CPU, SQL, Next.js, queues.
- [`RELEASE_CHECKLIST.md`](./RELEASE_CHECKLIST.md) — checklist de release et rollback.
- [`V93_GO_LIVE.md`](./V93_GO_LIVE.md) — contrat go-live V93.

## 4. Environnements

### Développement local

```bash
cp .env.docker.example .env
docker compose -f docker-compose.dev.yml up -d --build
```

Contrôles :

```bash
docker compose -f docker-compose.dev.yml ps
docker compose -f docker-compose.dev.yml exec backend python manage.py check
docker compose -f docker-compose.dev.yml exec frontend npm run test:ci
```

### Staging

Doit reproduire la topologie production : PostgreSQL/Redis réels, stockage distant, workers séparés, HTTPS, TURN, fournisseurs en sandbox/test lorsque possible.

### Production

- `DEBUG=False`
- `TEST_PAYMENTS_ENABLED=False`
- `SEED_DEMO=False`
- `USE_HTTPS=True`
- `USE_S3=True`
- `REQUIRE_REMOTE_MEDIA=True`
- `MALWARE_SCAN_REQUIRED=True`
- `RUN_MIGRATIONS_ON_BOOT=False` lorsque les migrations sont exécutées en Pre-deploy Railway.

## 5. Healthchecks

### Liveness

```text
GET /api/health/live/
```

Le liveness dit uniquement que le processus répond. Il ne doit pas devenir rouge parce que PostgreSQL ou Redis est temporairement indisponible.

### Readiness

```text
GET /api/health/ready/
```

Le readiness vérifie les dépendances critiques et peut retourner `503` lors d’une panne DB/cache. C’est normal et intentionnel.

### Frontend

```text
GET /healthz
```

### Santé plateforme admin

```text
GET /api/ops/health/
GET /api/ops/health/?scan_storage=1
```

Le second mode déclenche un scan borné du stockage et doit être utilisé ponctuellement.

## 6. Gates obligatoires avant release

Backend :

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test apps.common apps.payments apps.accounts apps.formations
python manage.py release_gate --strict-infra --deploy --production --json
```

Frontend :

```bash
npm run test:ci
npm run build:check
npm run production:preflight
```

Post-déploiement :

```bash
RELEASE_BASE_URL=https://<frontend> \
RELEASE_BACKEND_URL=https://<backend> \
npm run release:smoke:prod
```

## 7. Procédures d’exploitation à connaître

### Paiements

```bash
python manage.py reconcile_payments
python manage.py reconcile_payments --stale-only
```

### Premium

```bash
python manage.py premium_revenue_report --json
python manage.py premium_revenue_report --fail-on-past-due
```

### Live/WebRTC

```bash
python manage.py rtc_capacity_report --json
python manage.py rtc_capacity_report --fail-on-sfu-recommended
```

### Médias existants vers S3/R2

```bash
python manage.py migrate_local_media_to_storage --source /app/media
python manage.py migrate_local_media_to_storage --source /app/media --apply
```

Toujours exécuter d’abord le dry-run.

### Sauvegarde DB

```bash
python manage.py backup_database --upload --delete-local-after-upload
```

### Restauration DB

```bash
python manage.py restore_database --storage-key backups/database/<fichier>.dump --confirm
```

La restauration est une opération destructive au niveau logique et doit suivre le runbook PRA.

## 8. Fréquence de maintenance recommandée

### Quotidien

- vérifier Admin → Santé plateforme ;
- vérifier anomalies de paiement ;
- vérifier files Celery et HLS en échec ;
- vérifier emails/WhatsApp échoués ;
- vérifier erreurs de déploiement et disponibilité externe.

### Hebdomadaire

- exécuter `premium_revenue_report --json` ;
- exécuter `rtc_capacity_report --json` ;
- vérifier backups récents et leur taille ;
- vérifier multipart abandonnés / pipeline HLS ;
- vérifier dépendances avec correctifs de sécurité disponibles.

### Mensuel

- test de restauration sur staging ;
- audit des comptes administrateurs et accès fournisseurs ;
- revue coûts Railway/Vercel/S3/Redis/PostgreSQL ;
- revue des seuils de performance et capacité ;
- mise à jour planifiée des dépendances avec gates complets.

### Trimestriel

- exercice PRA complet ;
- rotation des secrets les plus sensibles ;
- revue des webhooks et domaines ;
- test TURN sur réseaux mobiles/restrictifs ;
- audit des permissions stockage et bucket.

## 9. Logs utiles

Docker local :

```bash
docker compose -f docker-compose.dev.yml logs -f backend
docker compose -f docker-compose.dev.yml logs -f celery_worker
docker compose -f docker-compose.dev.yml logs -f celery_media_worker
docker compose -f docker-compose.dev.yml logs -f celery_beat
docker compose -f docker-compose.dev.yml logs -f frontend
```

Production : utiliser les logs Railway/Vercel avec le `request_id` KalanPro pour corréler frontend/backend.

## 10. Nommage historique

Le projet s’appelle **KalanPro**, mais certains noms techniques historiques restent `learneas` : package Django, noms de conteneurs Docker, base par défaut et module Celery (`-A learneas`). Ne pas les renommer partiellement en production sans migration coordonnée.

## 11. Références externes

À revalider lors d’un changement majeur des plateformes :

- Railway healthchecks : https://docs.railway.com/deployments/healthchecks
- Railway Pre-deploy : https://docs.railway.com/deployments/pre-deploy-command
- Railway variables : https://docs.railway.com/variables
- Vercel monorepos/root directory : https://vercel.com/docs/monorepos
- Vercel build configuration : https://vercel.com/docs/builds/configure-a-build
- Vercel rollback : https://vercel.com/docs/deployments/rollback-production-deployment
- Next.js variables publiques : https://nextjs.org/docs/app/guides/environment-variables
