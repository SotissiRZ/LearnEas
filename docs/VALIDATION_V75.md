# Validation KalanPro v75 — Recruiter Workspace

## Contrôles exécutés dans l'environnement de génération

- Parsing AST Python de l'ensemble du backend : **224 fichiers valides**.
- Graphe statique des migrations Django : **61 migrations, aucun cycle détecté**.
- Parsing syntaxique TypeScript/TSX : **138 fichiers valides**.
- Tests frontend rôle employeur / Recruiter Workspace : **6/6**.
- Tests frontend performance : **5/5**.
- Tests frontend sécurité : **4/4**.
- Audit responsive/mobile : **122 fichiers inspectés, aucune alerte bloquante**.
- Contrôle des marqueurs de conflit Git : aucun marqueur détecté.

## Validation runtime à rejouer dans Docker

L'environnement de génération ne contient pas Django ni les `node_modules` du projet. Les validations runtime suivantes doivent donc être exécutées après extraction :

```bash
docker compose -f docker-compose.dev.yml up --build

docker compose -f docker-compose.dev.yml exec backend python manage.py check
docker compose -f docker-compose.dev.yml exec backend python manage.py makemigrations --check --dry-run
docker compose -f docker-compose.dev.yml exec backend python manage.py migrate --noinput
docker compose -f docker-compose.dev.yml exec backend python manage.py test apps.opportunities
```

Le lot v75 ajoute uniquement une migration additive (`opportunities.0003_recruiter_workspace`) pour le branding entreprise, les visuels d'offres, les métadonnées ATS et les favoris talents. Aucune suppression de table ou de colonne existante n'est effectuée.
