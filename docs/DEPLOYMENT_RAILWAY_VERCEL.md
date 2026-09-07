# KalanPro — Déploiement Railway + Vercel

Ce runbook décrit le déploiement **staging puis production** de KalanPro V93.4.

## 1. Pré-requis

- dépôt Git propre et version/tag identifié ;
- backend tests verts ;
- frontend `test:ci` + `build:check` verts ;
- PostgreSQL et Redis provisionnés ;
- bucket S3/R2 privé provisionné ;
- domaine backend et frontend disponibles ;
- fournisseur email configuré ;
- au moins un fournisseur de paiement production configuré si `PRODUCTION_REQUIRE_PAYMENT_PROVIDER=True` ;
- ClamAV joignable si scan obligatoire ;
- TURN configuré si `PRODUCTION_REQUIRE_TURN=True` ;
- sauvegarde DB récente avant toute migration sensible.

## 2. Topologie Railway

Créer un projet Railway avec deux environnements : `staging` et `production`.

### Backend web

- Source : dépôt KalanPro.
- Root Directory : `backend`.
- Builder : Dockerfile.
- Start command : laisser l’image utiliser `/app/docker/start-web.sh`.
- Healthcheck path : `/api/health/live/`.
- Le processus écoute automatiquement `${PORT:-8000}`.

Railway injecte `PORT` et l’utilise pour les healthchecks. Ne pas remettre un port fixe dans la commande de production.

### Pre-deploy backend

```bash
python manage.py migrate --noinput && python manage.py production_preflight --json
```

Configurer un timeout explicite adapté à la durée maximale raisonnable des migrations.

Variables runtime :

```env
RUN_MIGRATIONS_ON_BOOT=False
COLLECTSTATIC_ON_BOOT=True
```

Les migrations ne doivent pas être exécutées simultanément par le backend et les workers.

### Worker Celery général

Root Directory : `backend`.

```bash
celery -A learneas worker --loglevel=info -Q default,notifications
```

```env
SKIP_BOOTSTRAP=true
```

### Worker média

```bash
celery -A learneas worker --loglevel=info -Q media --concurrency=1 --prefetch-multiplier=1
```

```env
SKIP_BOOTSTRAP=true
```

Augmenter la concurrence média uniquement après mesure CPU/RAM/ffmpeg et stockage.

### Celery Beat

```bash
celery -A learneas beat --loglevel=info
```

```env
SKIP_BOOTSTRAP=true
```

**Une seule instance de Beat** par environnement.

### PostgreSQL / Redis

- privés ;
- aucune exposition Internet inutile ;
- sauvegardes/PITR du fournisseur activés lorsque le plan le permet ;
- `DATABASE_URL` et `REDIS_URL` injectés dans tous les services backend/Celery.

## 3. Variables backend minimales

Partir de `.env.production.example` et remplacer toutes les valeurs fictives.

Variables critiques :

```env
SECRET_KEY=<longue valeur aléatoire>
DEBUG=False
TEST_PAYMENTS_ENABLED=False
SEED_DEMO=False
USE_HTTPS=True

ALLOWED_HOSTS=api.example.com,healthcheck.railway.app
CORS_ALLOWED_ORIGINS=https://www.example.com
CSRF_TRUSTED_ORIGINS=https://www.example.com
REALTIME_ALLOWED_ORIGINS=https://www.example.com
FRONTEND_URL=https://www.example.com
BACKEND_PUBLIC_URL=https://api.example.com

DATABASE_URL=<railway-postgres>
REDIS_URL=<railway-redis>

USE_S3=True
REQUIRE_REMOTE_MEDIA=True
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_STORAGE_BUCKET_NAME=...
AWS_S3_ENDPOINT_URL=...

AUTH_REFRESH_COOKIE_SECURE=True
AUTH_REFRESH_COOKIE_SAMESITE=Lax
```

`healthcheck.railway.app` doit être accepté si les restrictions d’host Django bloquent la sonde Railway.

## 4. Médias S3/R2

Production :

```env
USE_S3=True
REQUIRE_REMOTE_MEDIA=True
DIRECT_MEDIA_UPLOADS_ENABLED=True
PUBLIC_MEDIA_BASE_URL=https://media.example.com
NEXT_PUBLIC_MEDIA_ORIGIN=https://media.example.com
```

Règles :

- bucket privé ;
- documents sensibles via URL présignée ;
- `PUBLIC_MEDIA_BASE_URL` uniquement pour les préfixes explicitement publics ;
- lifecycle fournisseur pour multipart abandonnés en seconde protection ;
- CORS bucket limité au domaine frontend ;
- tester upload vidéo multipart, HLS, PDF, portfolio et téléchargement privé avant promotion.

## 5. TURN/WebRTC

```env
RTC_STUN_URLS=stun:stun.l.google.com:19302
RTC_TURN_URLS=turn:turn.example.com:3478?transport=udp,turns:turn.example.com:5349?transport=tcp
RTC_TURN_SECRET=<secret partagé coturn REST>
RTC_ICE_TRANSPORT_POLICY=all
```

Tester au minimum : Wi-Fi, 4G/5G, réseau entreprise/restrictif.

## 6. Vercel frontend

Créer un projet Vercel connecté au même dépôt.

- Framework : Next.js.
- Root Directory : `frontend`.
- Production branch : branche de production choisie par l’équipe.

Variables :

```env
NEXT_PUBLIC_API_URL=/api
API_PROXY_TARGET=https://api.example.com
NEXT_PUBLIC_WS_URL=wss://api.example.com/ws
NEXT_PUBLIC_MEDIA_ORIGIN=https://media.example.com
NEXT_PUBLIC_API_TIMEOUT_MS=15000
NEXT_PUBLIC_UPLOAD_TIMEOUT_MS=600000
NEXT_PUBLIC_UPLOAD_PART_TIMEOUT_MS=300000
```

`API_PROXY_TARGET` est **serveur-only** et ne doit pas commencer par `NEXT_PUBLIC_`.

### Build Vercel recommandé

Dans CI :

```bash
npm ci
npm run production:preflight
npm run test:ci
npm run build:check
```

Pour le déploiement Vercel lui-même, utiliser le build Next.js standard après validation du preflight. Toute modification des `NEXT_PUBLIC_*` exige un nouveau build.

## 7. Webhooks

Pointer directement vers Railway :

```text
Stripe      /api/payments/stripe/webhook/
GeniusPay   /api/payments/geniuspay/webhook/
CinetPay    /api/payments/cinetpay/webhook/
CinetPay return /api/payments/cinetpay/return/
WhatsApp    /api/notifications/whatsapp/webhook/
```

Ne pas utiliser une URL Preview Vercel pour les callbacks production.

Après modification d’un secret webhook : tester la signature et un événement sandbox/test avant trafic réel.

## 8. Déploiement staging

1. Déployer PostgreSQL, Redis, stockage, backend, workers, Beat.
2. Exécuter le Pre-deploy.
3. Vérifier :

```bash
python manage.py production_preflight --json
python manage.py release_gate --strict-infra --deploy --production --json
```

4. Déployer Vercel staging.
5. Exécuter :

```bash
RELEASE_BASE_URL=https://<staging-frontend> \
RELEASE_BACKEND_URL=https://<staging-backend> \
npm run release:smoke:prod
```

6. Tester manuellement : login, création compte, achat sandbox, email, WhatsApp dry-run/test, upload vidéo, HLS, live, support, recruteur.
7. Vérifier Admin → Santé plateforme.

## 9. Promotion production

Avant promotion :

```bash
python manage.py backup_database --upload --delete-local-after-upload
```

Puis :

1. tag/release Git ;
2. déployer backend + pre-deploy ;
3. vérifier `/api/health/live/` et `/api/health/ready/` ;
4. déployer/promouvoir Vercel ;
5. smoke production ;
6. vérifier paiements/webhooks ;
7. vérifier queues Celery, HLS, email, Premium ;
8. surveiller 30–60 minutes après release.

## 10. Rollback

### Frontend Vercel

Utiliser l’interface Deployments ou `vercel rollback` vers un déploiement connu comme sain, puis refaire le smoke.

### Backend Railway

Revenir au dernier déploiement applicatif sain. Ne pas restaurer la DB automatiquement.

### Base de données

Restaurer uniquement si :

- migration destructive ;
- corruption ;
- erreur de données impossible à corriger applicativement.

```bash
python manage.py restore_database --storage-key backups/database/<fichier>.dump --confirm
```

## 11. Références officielles

- Railway healthchecks : https://docs.railway.com/deployments/healthchecks
- Railway pre-deploy : https://docs.railway.com/deployments/pre-deploy-command
- Railway variables : https://docs.railway.com/variables
- Vercel monorepo/root directory : https://vercel.com/docs/monorepos
- Vercel build : https://vercel.com/docs/builds/configure-a-build
- Vercel rollback : https://vercel.com/docs/deployments/rollback-production-deployment
