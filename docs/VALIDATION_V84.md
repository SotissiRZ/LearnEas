# Validation v84

Contrôles exécutés dans l'environnement de génération :

- 57/57 tests frontend statiques ;
- audit mobile : 129 fichiers, aucune alerte bloquante ;
- parsing syntaxique : 145 fichiers TypeScript/TSX, 0 erreur ;
- compilation syntaxique : 250 fichiers Python, 0 erreur ;
- scan de secrets : OK ;
- Docker Compose dev/prod : YAML valide ;
- entrypoint backend : syntaxe shell valide ;
- graphe migrations : 73 migrations, 0 collision, 0 dépendance interne manquante, 0 cycle ;
- 222 fonctions de tests backend recensées.

Release gates à exécuter dans Docker/CI :

```powershell
docker compose -f docker-compose.dev.yml exec backend python manage.py migrate
docker compose -f docker-compose.dev.yml exec backend python manage.py check
docker compose -f docker-compose.dev.yml exec backend python manage.py makemigrations --check --dry-run
docker compose -f docker-compose.dev.yml exec backend python manage.py test apps.projects apps.enrollments
docker compose -f docker-compose.dev.yml exec backend python manage.py test
docker compose -f docker-compose.dev.yml exec frontend npm run test:ci
docker compose -f docker-compose.dev.yml exec frontend npm run build:check
```

La migration v84 est additive : `projects.0002_portfolio_evidence_v84`.
