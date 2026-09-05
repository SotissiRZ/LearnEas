# KalanPro v81 — faible connexion, validation réelle et hors connexion

## Objectif

Rendre les cours vidéo utilisables sur les réseaux mobiles instables tout en conservant trois garanties :

1. le serveur reste l'autorité pour les droits d'accès ;
2. un saut dans la timeline ne doit pas transformer une vidéo non regardée en vidéo terminée ;
3. une copie hors connexion n'est créée que si l'instructeur l'autorise explicitement.

## Streaming adaptatif

Le paquet HLS unique peut contenir jusqu'à 240p/360p/480p/720p ainsi qu'une playlist audio seule ~48 kb/s. Le master privé supporte une politique signée `max_height`, ce qui permet de servir le même paquet avec uniquement les variantes <= `HLS_DATA_SAVER_MAX_HEIGHT`.

Le lecteur propose :

- **Auto** : adaptation au débit réel ; économie automatique sur `Save-Data`, 2G/slow-2G ou très faible downlink ;
- **Éco** : master privé plafonné à 360p par défaut ;
- **Normal** : toutes les variantes autorisées ;
- **Audio uniquement** : playlist AAC basse consommation.

La Network Information API expose principalement `slow-2g`, `2g`, `3g` et `4g`. Elle ne permet généralement pas d'affirmer qu'une radio est 5G. KalanPro affiche donc **Connexion rapide (4G/5G)** lorsqu'un `4g` effectif est accompagné d'un débit élevé, et supporte aussi un futur `effectiveType="5g"` sans prétendre que cette valeur est disponible partout.

## Validation réelle d'une vidéo

Chaque cours possède `video_completion_threshold_percent`, entre 50 et 100 %, **90 % par défaut**.

Pour une vidéo hébergée par KalanPro :

- `position_seconds` sert uniquement à la reprise ;
- `watched_delta_seconds` représente le temps effectivement lu ;
- le backend limite le crédit par rapport au temps mural depuis le dernier heartbeat (marge maximale 2,2x pour tenir compte des vitesses de lecture autorisées) ;
- l'ancien payload `watched_seconds=position` ne crédite plus de temps sur une vidéo gérée ;
- `mark_lesson_complete` renvoie `409` tant que le seuil n'est pas atteint.

Le bouton frontend est également désactivé avant le seuil, mais cette protection UI n'est pas considérée comme une frontière de sécurité : le backend refait le contrôle.

## Téléchargement hors connexion

L'instructeur active `offline_download_allowed` leçon par leçon. Lors de la préparation HLS, le worker génère alors `offline.mp4` :

- H.264/AAC ;
- `faststart` ;
- hauteur maximale `OFFLINE_VIDEO_MAX_HEIGHT` (360 par défaut) ;
- taille maximale `OFFLINE_VIDEO_MAX_MB` (250 Mo par défaut).

Si la copie dépasse la limite, elle est supprimée et n'est pas proposée au téléchargement.

Le serializer ne renvoie le lien privé signé et le jeton de progression qu'à un utilisateur authentifié ayant réellement accès à la leçon. Une leçon verrouillée ne divulgue ni chemin, ni taille, ni token.

## Stockage navigateur

Le téléchargement est stocké dans IndexedDB (`kalanpro-offline-media`). Depuis v81, chaque enregistrement est rattaché à `userId + courseId + lessonId`. L'upgrade v1 → v2 efface les anciennes copies non cloisonnées pour éviter qu'un second compte sur le même appareil puisse les retrouver via l'interface.

Avant téléchargement, KalanPro consulte `navigator.storage.estimate()` et demande le stockage persistant lorsque le navigateur le permet.

## Bibliothèque réellement accessible hors ligne

Le frontend enregistre `/kalanpro-sw.js`. Ce Service Worker met en cache uniquement la petite coque dédiée :

- `/offline-player.html` ;
- `/offline-player.js`.

Il n'intercepte pas les API, le checkout ou les pages authentifiées générales. La bibliothèque peut donc être rouverte après redémarrage du navigateur sans réseau, sans mettre en cache des pages sensibles.

La page autonome lit directement les vidéos IndexedDB du dernier utilisateur local actif et permet lecture/suppression. Son JavaScript est externe et une CSP dédiée bloque les connexions réseau et les scripts inline.

## Progression hors ligne

Pendant la lecture hors ligne :

- la position et le temps lu sont conservés sous `kalanpro:resume:<user>:<course>` ;
- `offlinePending=true` distingue ce temps d'un heartbeat en ligne ;
- le token signé `kalanpro.offline-progress` lie la copie à l'utilisateur et à la leçon ;
- au retour du réseau, le frontend resynchronise automatiquement ;
- le serveur plafonne le crédit au temps mural écoulé ;
- la réponse contient `credited_watched_seconds` ; si seule une partie est acceptée, le reste demeure local et n'est pas perdu.

## Limites de sécurité

Le mode hors connexion web est un **cache contrôlé**, pas un DRM absolu. Un utilisateur ayant le contrôle complet de son navigateur/appareil peut inspecter son stockage local. Pour une protection de niveau Netflix/Prime Video, il faudrait une application native/packagée et un DRM tel que Widevine/FairPlay/PlayReady avec licences offline.

## Variables

```env
HLS_STREAMING_ENABLED=True
HLS_MAX_HEIGHT=720
HLS_SEGMENT_SECONDS=6
HLS_DATA_SAVER_MAX_HEIGHT=360
HLS_AUDIO_ONLY_BITRATE=48k
HLS_SEGMENT_CACHE_SECONDS=600
HLS_TRANSCODE_TIMEOUT_SECONDS=7200
HLS_TRANSCODE_PRESET=veryfast

OFFLINE_VIDEO_ENABLED=True
OFFLINE_VIDEO_MAX_HEIGHT=360
OFFLINE_VIDEO_MAX_MB=250
OFFLINE_PROGRESS_TOKEN_MAX_AGE=2592000
```

## Vidéos existantes

Les masters HLS existants bénéficient immédiatement du filtrage faible débit. Pour une leçon existante à rendre hors connexion, activez **Hors ligne** dans l'espace instructeur : KalanPro relance la préparation et génère la copie basse définition.

Une régénération globale reste possible :

```bash
docker compose -f docker-compose.dev.yml exec backend python manage.py prepare_course_streaming --force
```

À lancer progressivement sur un gros catalogue, car le transcodage consomme CPU et stockage.

## Validation Docker

```bash
docker compose -f docker-compose.dev.yml exec backend python manage.py migrate
docker compose -f docker-compose.dev.yml exec backend python manage.py check
docker compose -f docker-compose.dev.yml exec backend python manage.py makemigrations --check --dry-run
docker compose -f docker-compose.dev.yml exec backend python manage.py test apps.catalog apps.enrollments
docker compose -f docker-compose.dev.yml exec backend python manage.py test
docker compose -f docker-compose.dev.yml exec frontend npm run test:ci
docker compose -f docker-compose.dev.yml exec frontend npm run build:check
```
