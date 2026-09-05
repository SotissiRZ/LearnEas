# Validation KalanPro v82

## Release gates statiques

- Python `compileall`
- parsing TypeScript/TSX de l'ensemble du frontend
- tests Node `test:unit`
- audit mobile
- scan de secrets
- validation YAML des deux fichiers Compose
- cohérence du graphe des migrations

## Release gates Docker à exécuter

```bash
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.dev.yml up -d --build

docker compose -f docker-compose.dev.yml exec backend python manage.py migrate
docker compose -f docker-compose.dev.yml exec backend python manage.py check
docker compose -f docker-compose.dev.yml exec backend python manage.py makemigrations --check --dry-run
docker compose -f docker-compose.dev.yml exec backend python manage.py test apps.notifications apps.opportunities
docker compose -f docker-compose.dev.yml exec backend python manage.py test

docker compose -f docker-compose.dev.yml exec frontend npm run test:ci
docker compose -f docker-compose.dev.yml exec frontend npm run build:check
```

## Scénarios manuels

1. Se connecter avec un apprenant : la cloche apparaît et `/notifications` est accessible.
2. Déposer une candidature : le recruteur reçoit une notification interne.
3. Changer l'étape ATS : le candidat reçoit une notification.
4. Planifier un entretien : notification immédiate, puis rappel ~60 min avant via Celery Beat.
5. Créer une offre : le candidat reçoit la notification ; accepter/refuser prévient le recruteur.
6. En `WHATSAPP_DRY_RUN=True`, activer WhatsApp et vérifier les lignes `WhatsAppDelivery` en statut `simulated`.
7. Désactiver la catégorie recrutement dans les préférences : l'in-app reste selon `in_app_enabled`, les canaux externes respectent leurs toggles.
