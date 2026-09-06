# Validation v87

Après extraction de l'archive :

```bash
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.dev.yml up -d --build

docker compose -f docker-compose.dev.yml exec backend python manage.py migrate
docker compose -f docker-compose.dev.yml exec backend python manage.py check
docker compose -f docker-compose.dev.yml exec backend python manage.py makemigrations --check --dry-run

docker compose -f docker-compose.dev.yml exec backend python manage.py test apps.analytics
docker compose -f docker-compose.dev.yml exec backend python manage.py test

docker compose -f docker-compose.dev.yml exec frontend npm run test:ci
docker compose -f docker-compose.dev.yml exec frontend npm run build:check
```

Toujours sans `down -v`.

## Tests manuels

1. Ouvrir plusieurs pages publiques puis **Admin → Analytics** et vérifier que les pages vues apparaissent.
2. Lancer une recherche et ouvrir un résultat ; vérifier l'augmentation des événements sans présence du texte recherché en base.
3. Lire puis terminer une vidéo de cours ; vérifier `video_started` / `video_completed`.
4. Vérifier les périodes 7/30/90/365 jours.
5. Exporter le CSV.
6. Vérifier qu'un étudiant reçoit `403` sur `/api/analytics/admin/overview/`.
7. Vérifier qu'une URL de reset password n'est pas conservée dans `ProductEvent.path`.

## Correctif harness Docker v87

La suite frontend contient des tests structurels qui inspectent aussi le backend, les fichiers Compose, la CI et nginx. En Docker dev, le frontend reste monté sur `/app`, tandis que ces sources sont exposées séparément en lecture seule sous `/workspace` via `KALANPRO_REPO_ROOT=/workspace`.

Le helper `frontend/scripts/test-paths.mjs` résout désormais les chemins à partir de l'emplacement réel des scripts et de `KALANPRO_REPO_ROOT`, sans dépendre de `process.cwd()` ni de chemins `../` qui remontaient auparavant vers `/backend`, `/.github` ou `/docker-compose.dev.yml`.

Après modification de `docker-compose.dev.yml`, recréer les conteneurs sans supprimer les volumes :

```bash
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.dev.yml up -d --build
docker compose -f docker-compose.dev.yml exec frontend npm run test:unit
```

Résultat de référence du correctif : **71 tests, 71 réussis, 0 échec**.
