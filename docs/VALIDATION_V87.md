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
