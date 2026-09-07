# KalanPro V93 — Go-live Railway + Vercel

## Objectif
V93 clôt la roadmap pré-production. Elle ne rajoute pas de fonctionnalité métier : elle rend la pile V92 déployable, contrôlable et réversible.

## Railway — services recommandés
Créer un environnement **staging** avant **production**. Utiliser le dépôt monorepo avec le répertoire racine `backend` pour les services Python.

| Service | Public | Start command | Notes |
|---|---|---|---|
| backend | oui | image Docker par défaut (`/app/docker/start-web.sh`) | écoute `${PORT:-8000}`, health `/api/health/live/` |
| celery-worker | non | `celery -A learneas worker --loglevel=info -Q default,notifications` | `SKIP_BOOTSTRAP=true` |
| celery-media | non | `celery -A learneas worker --loglevel=info -Q media --concurrency=1 --prefetch-multiplier=1` | `SKIP_BOOTSTRAP=true` |
| celery-beat | non | `celery -A learneas beat --loglevel=info` | une seule instance, `SKIP_BOOTSTRAP=true` |
| PostgreSQL | non | service managé | sauvegardes/PITR à activer selon le plan |
| Redis | non | service managé | cache, Channels et Celery |

Pour le backend Railway, configurer le **Pre-deploy command** :

```bash
python manage.py migrate --noinput && python manage.py production_preflight --json
```

Puis utiliser au runtime :

```env
RUN_MIGRATIONS_ON_BOOT=False
COLLECTSTATIC_ON_BOOT=True
```

Avant de promouvoir staging vers production :

```bash
python manage.py release_gate --strict-infra --deploy --production --json
```

## Vercel — frontend
Créer un projet avec Root Directory `frontend`. Garder Next.js natif et configurer les variables dans les Project Settings.

```env
NEXT_PUBLIC_API_URL=/api
API_PROXY_TARGET=https://<backend-railway>
NEXT_PUBLIC_WS_URL=wss://<backend-railway>/ws
NEXT_PUBLIC_MEDIA_ORIGIN=https://<cdn-media>
NEXT_PUBLIC_API_TIMEOUT_MS=15000
NEXT_PUBLIC_UPLOAD_TIMEOUT_MS=600000
NEXT_PUBLIC_UPLOAD_PART_TIMEOUT_MS=300000
```

`API_PROXY_TARGET` est serveur-only. Ne jamais exposer de secret sous un nom `NEXT_PUBLIC_*`.

Avant build/deploy :

```bash
npm run production:preflight
npm run test:ci
npm run build:check
```

## Webhooks publics
Les webhooks externes doivent viser directement le backend Railway :

- Stripe : `/api/payments/stripe/webhook/`
- GeniusPay : `/api/payments/geniuspay/webhook/`
- CinetPay : `/api/payments/cinetpay/webhook/`
- CinetPay return : `/api/payments/cinetpay/return/`
- WhatsApp Meta : `/api/notifications/whatsapp/webhook/`

Ne pas utiliser une URL de preview Vercel pour ces callbacks de production.

## Médias
Production requiert `USE_S3=True` et `REQUIRE_REMOTE_MEDIA=True`. Le bucket doit rester privé ; `PUBLIC_MEDIA_BASE_URL` ne sert que les préfixes explicitement publics. Les gros uploads vidéo passent directement navigateur -> S3/R2 en multipart.

## Sauvegarde avant migration sensible

```bash
python manage.py backup_database --upload --delete-local-after-upload
```

La clé est créée sous `backups/database/`. Une restauration exige une confirmation explicite :

```bash
python manage.py restore_database --storage-key backups/database/<fichier>.dump --confirm
```

## Post-déploiement
Depuis `frontend` :

```bash
RELEASE_BASE_URL=https://<frontend> \
RELEASE_BACKEND_URL=https://<backend> \
npm run release:smoke:prod
```

Le smoke vérifie HTTPS, liveness/readiness, proxy same-origin, CORS direct Railway, CSP, pages publiques et catalogues.

## Rollback
1. Ne pas inverser automatiquement une migration additive déjà appliquée.
2. Revenir au dernier déploiement applicatif connu comme sain.
3. Exécuter le smoke post-déploiement.
4. Restaurer PostgreSQL uniquement si une migration destructive ou une corruption de données le justifie et après validation explicite de la sauvegarde.
5. Conserver les écritures financières/audit ; ne jamais les supprimer pour « corriger » un rollback applicatif.
