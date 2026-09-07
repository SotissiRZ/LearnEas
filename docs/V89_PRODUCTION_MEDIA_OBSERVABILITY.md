# KalanPro V89 — Production Media & Observability

## Objectif

V89 transforme les briques média déjà présentes en socle exploitable en production, sans changer le modèle métier V88.

### Stockage média

- `USE_S3=False` conserve le stockage disque pour Docker/dev.
- `USE_S3=True` utilise désormais `KalanProS3Storage`, compatible AWS S3, Cloudflare R2, Backblaze et endpoints S3 compatibles.
- Les objets sensibles restent privés et utilisent explicitement des URLs S3/R2 présignées, même si un `AWS_S3_CUSTOM_DOMAIN` historique est renseigné.
- Les préfixes explicitement publics peuvent être servis via `PUBLIC_MEDIA_BASE_URL`, typiquement un CDN disposant d'un accès origine au bucket privé.
- Les objets publics reçoivent un cache long `public, max-age=..., immutable` ; les objets privés gardent `private, no-store`.
- Aucun secret S3 n'est envoyé au frontend.

`PUBLIC_MEDIA_BASE_URL` ne rend pas le bucket public par lui-même. Le CDN doit être configuré avec un accès origine approprié au bucket.

## HLS et vidéos privées

- Le multipart navigateur → S3/R2 de V79/V81 est conservé.
- Les segments HLS S3 reçoivent une surcharge de cache contrôlée lors de la génération de l'URL présignée.
- L'accès aux médias privés S3 n'effectue plus un `HEAD` supplémentaire avant chaque redirection présignée ; le fournisseur renvoie lui-même 404 si l'objet n'existe plus.
- Le pipeline ffmpeg/HLS continue d'écrire via `default_storage`, donc le même code fonctionne en local et sur S3/R2.

## Nettoyage des multipart abandonnés

La tâche Celery `apps.common.tasks.cleanup_stale_multipart_uploads` s'exécute toutes les six heures. Elle :

- ne fait rien en stockage local ;
- inspecte uniquement `courses/videos/direct/` ;
- abandonne les uploads plus anciens que `MULTIPART_UPLOAD_MAX_AGE_HOURS` ;
- est plafonnée par `MULTIPART_CLEANUP_MAX_ABORTS` pour éviter un nettoyage non borné.

Un lifecycle natif du fournisseur S3/R2 reste recommandé comme seconde protection.

## Migration des médias existants

La commande ne supprime jamais la source locale :

```bash
# simulation uniquement
docker compose exec backend python manage.py migrate_local_media_to_storage --source /app/media

# copie réelle vers le stockage distant actif
docker compose exec backend python manage.py migrate_local_media_to_storage --source /app/media --apply
```

Options : `--prefix` pour limiter à un répertoire et `--limit` pour procéder par lots.

## Santé plateforme

Nouvel endpoint admin-only :

`GET /api/ops/health/`

Il expose uniquement des données opérationnelles non sensibles :

- PostgreSQL ;
- cache Redis ;
- broker Celery et profondeur des files `default`, `notifications`, `media` ;
- backend de stockage et état S3/local ;
- multipart actifs/anciens ;
- pipeline HLS (pending/processing/ready/failed) ;
- anomalies financières ;
- tickets support/signalements ;
- échecs email/WhatsApp sur 24 h ;
- présence de configuration Resend/WhatsApp/IA/TURN sans révéler de clé.

`GET /api/ops/health/?scan_storage=1` ajoute une analyse bornée du bucket. Elle est volontairement déclenchée manuellement depuis le back-office afin de ne pas lister le bucket à chaque rafraîchissement.

## Interface admin

`Admin → Santé plateforme` présente :

- état global ;
- services critiques ;
- files Celery ;
- pipeline médias ;
- signaux finance/support/notifications ;
- stockage et multipart ;
- état de configuration des fournisseurs.

## Variables V89

```env
PUBLIC_MEDIA_BASE_URL=
MEDIA_PUBLIC_CACHE_SECONDS=31536000
MEDIA_PRIVATE_CACHE_CONTROL=private, no-store
S3_CONNECT_TIMEOUT_SECONDS=3
S3_READ_TIMEOUT_SECONDS=10
MULTIPART_UPLOAD_MAX_AGE_HOURS=24
MULTIPART_CLEANUP_MAX_ABORTS=200
OPERATIONS_STORAGE_SCAN_MAX_OBJECTS=2000
OPERATIONS_QUEUE_WARNING_DEPTH=100
```

Aucune nouvelle migration de base de données n'est requise par V89.
