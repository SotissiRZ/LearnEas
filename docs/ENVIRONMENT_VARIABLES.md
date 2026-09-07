# KalanPro — Référence des variables d’environnement

La source de vérité exécutable reste `.env.docker.example`, `.env.production.example`, `docker-compose*.yml` et les settings Django. Ce document explique **où** placer les variables et lesquelles sont critiques.

## 1. Principes

- secrets backend : Railway uniquement ;
- variables frontend serveur : Vercel sans préfixe `NEXT_PUBLIC_` ;
- variables client : uniquement `NEXT_PUBLIC_*` et uniquement valeurs non sensibles ;
- ne jamais committer `.env` réel ;
- utiliser des valeurs distinctes staging/production ;
- changer un `NEXT_PUBLIC_*` => nouveau build Vercel.

## 2. Django / sécurité

| Variable | Prod | Description |
|---|---:|---|
| `SECRET_KEY` | obligatoire | secret Django long/aléatoire |
| `DEBUG` | `False` | jamais `True` en prod |
| `TEST_PAYMENTS_ENABLED` | `False` | interdit en prod |
| `SEED_DEMO` | `False` | comptes démo interdits en prod |
| `USE_HTTPS` | `True` | cookies/redirects sécurité |
| `ALLOWED_HOSTS` | obligatoire | backend + host Railway healthcheck si nécessaire |
| `CORS_ALLOWED_ORIGINS` | obligatoire | domaines frontend exacts |
| `CSRF_TRUSTED_ORIGINS` | obligatoire | origines HTTPS exactes |
| `REALTIME_ALLOWED_ORIGINS` | obligatoire | WebSocket Channels |
| `FRONTEND_URL` | obligatoire | URL frontend publique |
| `BACKEND_PUBLIC_URL` | obligatoire | URL backend publique |
| `AUTH_REFRESH_COOKIE_SECURE` | `True` | cookie refresh HttpOnly sécurisé |

## 3. Base / Redis

| Variable | Service(s) | Description |
|---|---|---|
| `DATABASE_URL` | backend + workers | PostgreSQL |
| `REDIS_URL` | backend + workers | cache, Channels, broker |

## 4. Médias / S3

| Variable | Prod | Description |
|---|---:|---|
| `USE_S3` | `True` | active stockage distant |
| `REQUIRE_REMOTE_MEDIA` | `True` | bloque prod sans stockage distant |
| `AWS_ACCESS_KEY_ID` | obligatoire | secret S3/R2 |
| `AWS_SECRET_ACCESS_KEY` | obligatoire | secret S3/R2 |
| `AWS_STORAGE_BUCKET_NAME` | obligatoire | bucket |
| `AWS_S3_ENDPOINT_URL` | selon fournisseur | R2/S3 compatible |
| `AWS_S3_REGION_NAME` | selon fournisseur | région |
| `PUBLIC_MEDIA_BASE_URL` | recommandé | CDN médias explicitement publics |
| `DIRECT_MEDIA_UPLOADS_ENABLED` | `True` | multipart navigateur -> S3 |
| `DIRECT_UPLOAD_PART_SIZE_MB` | 16 | taille part multipart |
| `DIRECT_UPLOAD_URL_TTL_SECONDS` | 3600 | durée URL présignée |
| `MULTIPART_UPLOAD_MAX_AGE_HOURS` | 24 | nettoyage abandons |

## 5. HLS / vidéo

| Variable | Valeur typique |
|---|---:|
| `HLS_STREAMING_ENABLED` | `True` |
| `HLS_MAX_HEIGHT` | `720` |
| `HLS_SEGMENT_SECONDS` | `6` |
| `HLS_SEGMENT_CACHE_SECONDS` | `600` |
| `VIDEO_NORMALIZATION_ENABLED` | `True` |
| `VIDEO_TRANSCODE_TIMEOUT_SECONDS` | `3600` |
| `HLS_TRANSCODE_TIMEOUT_SECONDS` | `7200` |

## 6. Scan antivirus

| Variable | Prod |
|---|---:|
| `MALWARE_SCAN_ENABLED` | `True` |
| `MALWARE_SCAN_REQUIRED` | `True` |
| `CLAMAV_HOST` | obligatoire si scan requis |
| `CLAMAV_PORT` | `3310` |

## 7. Paiements

Au moins un fournisseur complet si `PRODUCTION_REQUIRE_PAYMENT_PROVIDER=True`.

### Stripe

```env
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PUBLISHABLE_KEY=
```

### GeniusPay

```env
GENIUSPAY_API_KEY=
GENIUSPAY_API_SECRET=
GENIUSPAY_WEBHOOK_SECRET=
```

### CinetPay

```env
CINETPAY_API_KEY=
CINETPAY_SITE_ID=
CINETPAY_SECRET_KEY=
```

### YouCanPay

```env
YOUCANPAY_ACCESS_TOKEN=
```

Variables communes :

```env
PAYMENT_CURRENCY=EUR
PLATFORM_COMMISSION_PERCENT=15
MINIMUM_PAYOUT_AMOUNT=10
```

## 8. Email / Resend

```env
PRODUCTION_REQUIRE_EMAIL=True
RESEND_ENABLED=True
RESEND_DRY_RUN=False
RESEND_API_KEY=
DEFAULT_FROM_EMAIL=KalanPro <no-reply@example.com>
```

Ou SMTP via `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, etc.

## 9. WhatsApp

```env
WHATSAPP_ENABLED=True
WHATSAPP_DRY_RUN=False
WHATSAPP_GRAPH_API_VERSION=v25.0
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_VERIFY_TOKEN=
WHATSAPP_APP_SECRET=
```

## 10. WebRTC / TURN

```env
PRODUCTION_REQUIRE_TURN=True
RTC_STUN_URLS=stun:stun.l.google.com:19302
RTC_TURN_URLS=
RTC_TURN_SECRET=
RTC_TURN_TTL_SECONDS=3600
RTC_MESH_SOFT_LIMIT=6
RTC_SFU_RECOMMEND_THRESHOLD=7
RTC_SFU_URL=
RTC_ICE_TRANSPORT_POLICY=all
```

`RTC_SFU_URL` reste vide tant qu’un véritable adaptateur SFU n’est pas déployé.

## 11. Premium

```env
PREMIUM_RENEWAL_LEAD_HOURS=72
PREMIUM_RENEWAL_GRACE_HOURS=48
PREMIUM_RENEWAL_BATCH_SIZE=100
PREMIUM_SETTLEMENT_BATCH_SIZE=200
```

Le pourcentage du pool créateurs est administrable en base via `PlatformSettings`, pas une variable d’environnement.

## 12. Frontend Vercel

### Public

```env
NEXT_PUBLIC_API_URL=/api
NEXT_PUBLIC_WS_URL=wss://api.example.com/ws
NEXT_PUBLIC_MEDIA_ORIGIN=https://media.example.com
NEXT_PUBLIC_API_TIMEOUT_MS=15000
NEXT_PUBLIC_UPLOAD_TIMEOUT_MS=600000
NEXT_PUBLIC_UPLOAD_PART_TIMEOUT_MS=300000
```

### Serveur-only

```env
API_PROXY_TARGET=https://api.example.com
PUBLIC_API_TIMEOUT_MS=8000
```

Ne jamais créer :

```text
NEXT_PUBLIC_SECRET_KEY
NEXT_PUBLIC_DATABASE_URL
NEXT_PUBLIC_STRIPE_SECRET_KEY
NEXT_PUBLIC_WHATSAPP_ACCESS_TOKEN
```

## 13. Go-live V93

```env
PRODUCTION_REQUIRE_PAYMENT_PROVIDER=True
PRODUCTION_REQUIRE_EMAIL=True
PRODUCTION_REQUIRE_TURN=True
PRODUCTION_REQUIRE_MALWARE_SCAN=True
RUN_MIGRATIONS_ON_BOOT=False
COLLECTSTATIC_ON_BOOT=True
DAPHNE_APPLICATION_CLOSE_TIMEOUT=10
```

## 14. Validation

Backend :

```bash
python manage.py production_preflight --json
python manage.py release_gate --strict-infra --deploy --production --json
```

Frontend :

```bash
npm run production:preflight
```

Un blocker doit être corrigé avant déploiement. Ne pas le contourner en désactivant arbitrairement les garde-fous.
