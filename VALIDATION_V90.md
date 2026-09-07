# Validation V90

## Résultats obtenus avant packaging

- `npm run test:unit` : **96/96 tests réussis**.
- `npm run audit:mobile` : **136 fichiers inspectés, aucune alerte bloquante**.
- Syntaxe Node des runners smoke/load/chaos : OK.
- Parsing/compilation Python : **289 fichiers, 0 erreur AST**.
- YAML : `docker-compose.dev.yml`, `docker-compose.yml`, `.github/workflows/ci.yml` valides.
- Scan secrets : OK.
- Harness des runners V90 validé sur un serveur HTTP local simulé : smoke authentifié OK, chaos 100 % de succès final sur le scénario de test, charge 0 % d'erreur.
- Diff V89 → V90 : aucune migration et aucun `models.py` modifiés.

L'environnement de génération ne contient pas Django ni Docker, donc les gates runtime Django/stack complète doivent être exécutés dans l'environnement Docker du projet.

## Gates statiques/localement exécutables

```bash
cd frontend
npm run test:unit
npm run audit:mobile
npm run typecheck
npm run build:check
```

```bash
cd backend
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test apps.common
```

## Gates runtime Docker

```bash
docker compose -f docker-compose.dev.yml exec backend python manage.py release_gate --json
docker compose -f docker-compose.dev.yml exec frontend npm run release:smoke:dev
docker compose -f docker-compose.dev.yml exec frontend npm run release:chaos
docker compose -f docker-compose.dev.yml exec frontend npm run release:load
```

Ou en un seul gate frontend :

```bash
docker compose -f docker-compose.dev.yml exec frontend npm run release:qualify:dev
```

## Staging/production

Après configuration réelle PostgreSQL, Redis, S3/R2, HTTPS et workers Celery :

```bash
python manage.py release_gate --strict-infra --deploy --json
```

Une release candidate n'est validée que si tous les gates ci-dessus sont verts.
