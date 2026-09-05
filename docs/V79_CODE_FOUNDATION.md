# KalanPro v79 — Fondation technique côté code

v79 est un lot de durcissement technique. Il ne change pas les règles métier et n'ajoute aucune migration de données.

## 1. CI et release gates

Le workflow `.github/workflows/ci.yml` exécute à chaque push/PR :

- scan interne de secrets à haute confiance ;
- validation syntaxique de l'entrypoint backend ;
- validation des deux fichiers Docker Compose ;
- installation backend + `pip check` ;
- `python manage.py check` ;
- `python manage.py makemigrations --check --dry-run` ;
- migrations sur PostgreSQL de CI ;
- suite Django complète ;
- `python manage.py check --deploy` avec une configuration proche production ;
- tests statiques frontend, audit mobile et typecheck ;
- build Next de production via `npm run build:check`.

## 2. Healthchecks

Trois URLs sont disponibles :

- `/api/health/live/` : liveness du processus Django, sans dépendance externe ;
- `/api/health/ready/` : readiness PostgreSQL + cache/Redis ;
- `/api/health/` : alias historique de la readiness.

Docker utilise désormais `/api/health/ready/`. Une indisponibilité Redis/PostgreSQL rend le service non prêt sans transformer la sonde de liveness en raison de redémarrage du processus.

## 3. Request-ID et logs structurés

Chaque requête reçoit un `X-Request-ID` :

- un identifiant entrant valide est conservé ;
- sinon KalanPro en génère un ;
- l'identifiant est renvoyé dans la réponse ;
- la méthode, le chemin, le statut et la durée sont journalisés avec cet identifiant.

`LOG_FORMAT=console` reste lisible en développement. `LOG_FORMAT=json` est prévu pour Railway/agrégateurs de logs en production.

Les erreurs API 5xx affichées par le frontend peuvent maintenant inclure la référence `X-Request-ID` afin de retrouver rapidement la requête correspondante dans les logs.

## 4. Résilience JWT et réseau

Le refresh JWT distingue désormais :

- `401/403` : refresh réellement invalide, la session locale est expirée ;
- timeout, erreur réseau, `5xx` ou réponse temporairement inexploitable : backend indisponible, sans fausse révocation de session.

Les timeouts sont bornés et configurables :

- `NEXT_PUBLIC_API_TIMEOUT_MS` : 15 s par défaut ;
- `NEXT_PUBLIC_UPLOAD_TIMEOUT_MS` : 10 min par défaut ;
- `NEXT_PUBLIC_UPLOAD_PART_TIMEOUT_MS` : 5 min par bloc multipart ;
- `PUBLIC_API_TIMEOUT_MS` : 8 s par défaut pour les requêtes publiques SSR.

Les uploads XHR, les blocs multipart directs et les téléchargements privés ne peuvent donc plus rester bloqués indéfiniment.

## 5. Uploads image

En plus de la taille/extension/signature existantes, toutes les images validées par `validate_upload_limits` sont contrôlées sur :

- dimension maximale : `MAX_IMAGE_DIMENSION=12000` px par défaut ;
- nombre maximal de pixels : `MAX_IMAGE_PIXELS=60000000` par défaut ;
- image invalide/corrompue/decompression bomb.

Le contrôle s'applique notamment aux avatars, miniatures de cours/formations, opportunités, profils entreprise et projets qui passent par les validateurs communs.

## 6. Erreurs frontend

`app/error.tsx` et `app/global-error.tsx` fournissent une récupération propre en cas d'erreur React/Next inattendue.

Le boundary de route envoie uniquement une télémétrie technique minimale vers `/api/telemetry/client-error/` : nom d'erreur, digest Next éventuel et pathname. Aucun message libre ni stack trace n'est transmis. L'endpoint est public mais throttlé (`CLIENT_TELEMETRY_THROTTLE_RATE`, 60/h par défaut).

## 7. Garde-fous production

Lorsque `DEBUG=False`, KalanPro refuse notamment :

- une `SECRET_KEY` de développement ou trop courte ;
- `ALLOWED_HOSTS=*` ;
- `AUTH_REFRESH_COOKIE_SECURE=False` ;
- `TEST_PAYMENTS_ENABLED=True` ;
- `SEED_DEMO=True` ;
- des origines CORS/realtime génériques ;
- des URLs/origines HTTP lorsque `USE_HTTPS=True`.

L'entrypoint backend refuse également `SEED_DEMO=True` avec `DEBUG=False` avant le bootstrap Django.

## 8. Sauvegarde PostgreSQL

L'image backend embarque `postgresql-client` et fournit :

```bash
python manage.py backup_database
python manage.py restore_database /app/backups/kalanpro-YYYYMMDDTHHMMSSZ.dump --confirm
```

`backup_database` utilise le format custom de `pg_dump`, sans propriétaire ni privilèges. `restore_database` exige explicitement `--confirm`.

Le dossier `/app/backups` est un volume Docker séparé en développement et dans le Compose principal. Une restauration doit toujours être testée sur une base non-production avant qu'une sauvegarde soit considérée comme exploitable.

## 9. Hygiène du dépôt et build Next

Le `.gitignore` racine exclut notamment secrets locaux, caches Python, médias runtime, sauvegardes, `node_modules`, `.next`, `.next-build-check`, coverage et artefacts Playwright.

`npm run build:check` utilise un `distDir` isolé et supprime `.next-build-check` même en cas d'échec. Il peut donc être lancé sans corrompre le `.next` utilisé par `next dev`.

## Validation Docker de la candidate v79

Après mise à jour du code :

```bash
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.dev.yml up -d --build

docker compose -f docker-compose.dev.yml exec backend python manage.py check
docker compose -f docker-compose.dev.yml exec backend python manage.py makemigrations --check --dry-run
docker compose -f docker-compose.dev.yml exec backend python manage.py test
docker compose -f docker-compose.dev.yml exec frontend npm run test:ci
docker compose -f docker-compose.dev.yml exec frontend npm run build:check
```

Ne pas utiliser `down -v` : v79 ne nécessite aucune réinitialisation de données.
