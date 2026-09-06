# Validation KalanPro v86

## Contrôles exécutés hors Docker

- `python -m compileall backend` : OK.
- Parsing AST Python complet : OK.
- Parsing syntaxique TypeScript/TSX via TypeScript : OK.
- `npm run test:unit` : 67/67 OK.
- `npm run audit:mobile` : 131 fichiers, aucune alerte bloquante.
- `python scripts/check_secrets.py` : OK.
- `bash -n backend/docker/entrypoint.sh` : OK.
- Parsing YAML `docker-compose.dev.yml` et `docker-compose.yml` : OK.
- 74 fichiers de migrations existants ; v86 n'en ajoute aucun.

## À rejouer dans Docker

```bash
docker compose -f docker-compose.dev.yml exec backend python manage.py check
docker compose -f docker-compose.dev.yml exec backend python manage.py makemigrations --check --dry-run
docker compose -f docker-compose.dev.yml exec backend python manage.py test apps.discovery
docker compose -f docker-compose.dev.yml exec backend python manage.py test

docker compose -f docker-compose.dev.yml exec frontend npm run test:ci
docker compose -f docker-compose.dev.yml exec frontend npm run build:check
```

## Tests fonctionnels recommandés

1. recherche anonyme sur un cours publié ;
2. confirmation qu'un cours brouillon n'apparaît pas ;
3. confirmation qu'un talent n'apparaît jamais en anonyme ;
4. compte recruteur Starter : aucun talent dans la recherche ;
5. compte recruteur Pro/Business : talents visibles uniquement s'ils sont `is_searchable` ;
6. compte candidat : recommandations d'offres et score match cohérents ;
7. navbar : suggestions et navigation vers `/search` ;
8. mobile 320–430 px : filtres horizontaux et cartes sans overflow.
