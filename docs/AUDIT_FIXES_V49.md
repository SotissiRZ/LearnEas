# KalanPro v49 — Correctifs audit P0

Cette version traite en priorité les blocages de production liés aux vidéos volumineuses et au stockage Railway.

## 1. Aucun FFmpeg/ffprobe dans la requête d'upload

`LessonWriteSerializer` ne lance plus de normalisation ni d'extraction de durée pendant la requête HTTP.
Il valide uniquement taille/extension, sauvegarde la leçon puis programme `normalize_lesson_video` via Celery après commit SQL.

Pipeline worker :

1. lecture de la source locale ou S3/R2 ;
2. ffprobe + contrôle de compatibilité navigateur ;
3. normalisation H.264/AAC uniquement si nécessaire ;
4. calcul de la durée réelle ;
5. sauvegarde de la version normalisée si nécessaire ;
6. génération HLS adaptative + audio faible débit.

Pour une source S3/R2, la source n'est matérialisée qu'une seule fois localement pour éviter un double téléchargement des vidéos volumineuses.

## 2. Upload multipart direct S3/R2

Lorsque `USE_S3=True` et `DIRECT_MEDIA_UPLOADS_ENABLED=True`, l'interface instructeur utilise :

- `GET /api/catalog/lessons/upload-capabilities/`
- `POST /api/catalog/lessons/direct-upload-start/`
- `POST /api/catalog/lessons/direct-upload-part/`
- upload `PUT` direct du bloc vers l'URL S3/R2 présignée ;
- `POST /api/catalog/lessons/direct-upload-complete/`
- `POST /api/catalog/lessons/direct-upload-abort/` en cas d'échec.

Les blocs sont signés au moment où ils sont nécessaires et chaque bloc est retenté jusqu'à trois fois. Les credentials S3 ne sont jamais exposés au frontend.

En développement local (`USE_S3=False`), le frontend conserve automatiquement l'ancien upload multipart HTTP vers Django, mais le traitement vidéo reste asynchrone.

### CORS du bucket

Le bucket doit autoriser `PUT` depuis le domaine KalanPro/Vercel et exposer `ETag` dans `ExposeHeaders` pour permettre la finalisation multipart.

## 3. Stockage distant en production

`REQUIRE_REMOTE_MEDIA` vaut désormais `not DEBUG` par défaut. Avec `DEBUG=False`, une configuration sans stockage distant échoue donc par défaut au démarrage au lieu de risquer de perdre les médias sur le disque éphémère Railway.

Variables ajoutées :

- `DIRECT_MEDIA_UPLOADS_ENABLED`
- `DIRECT_UPLOAD_PART_SIZE_MB` (défaut : 16)
- `DIRECT_UPLOAD_URL_TTL_SECONDS` (défaut : 3600)

## 4. Mobile

Les deux logos d'entreprise signalés par l'audit mobile utilisent maintenant `loading="lazy"` et `decoding="async"`.

Résultat du script : `OK · aucune alerte bloquante.`

## 5. Tests ajoutés

Des régressions backend couvrent :

- upload vidéo sans ffmpeg/ffprobe synchrone ;
- fallback local quand S3 est désactivé ;
- initialisation multipart pour le propriétaire ;
- finalisation multipart créant une leçon `pending`.

## Validation effectuée dans l'environnement d'audit

- `python -m compileall backend` : OK
- parsing/transpilation TypeScript ciblée des fichiers modifiés : OK
- `node frontend/scripts/audit-mobile.mjs` : OK

La suite Django et le build Next.js complets n'ont pas pu être exécutés dans l'environnement d'audit car les dépendances ne sont pas installées et l'accès réseau est indisponible. Ils restent des **release gates obligatoires** dans la CI/Docker avant déploiement.
