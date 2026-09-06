# Validation KalanPro v85

## Contrôles exécutés dans l'environnement de génération

- `npm run test:unit` : 63/63 tests statiques frontend OK.
- `npm run audit:mobile` : 129 fichiers inspectés, aucune alerte bloquante.
- Python : 251 fichiers compilés, 0 erreur de syntaxe.
- TypeScript/TSX : 143 fichiers contrôlés avec TypeScript, 0 erreur de parsing. Le typecheck complet n'est pas annoncé ici car `npm ci` n'a pas pu terminer dans l'environnement de génération (résolution npm indisponible/EAI_AGAIN).
- Scan de secrets : OK.
- YAML Compose dev/prod : OK.
- Entrypoint shell : syntaxe OK.
- Graphe local : 74 migrations, 0 dépendance locale manquante, 0 cycle, 0 branche concurrente.
- 225 fonctions de test backend recensées.

## Release gates Docker requis

Après extraction sur la machine de développement :

```powershell
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.dev.yml up -d --build

docker compose -f docker-compose.dev.yml exec backend python manage.py migrate
docker compose -f docker-compose.dev.yml exec backend python manage.py check
docker compose -f docker-compose.dev.yml exec backend python manage.py makemigrations --check --dry-run

docker compose -f docker-compose.dev.yml exec backend python manage.py test apps.opportunities apps.notifications
docker compose -f docker-compose.dev.yml exec backend python manage.py test

docker compose -f docker-compose.dev.yml exec frontend npm run test:ci
docker compose -f docker-compose.dev.yml exec frontend npm run build:check
```

Ne pas utiliser `down -v` : les volumes PostgreSQL doivent être conservés.

## Scénarios manuels prioritaires

1. Recruteur Pro/Business : ouvrir Vivier, sélectionner une offre et vérifier score + explication.
2. Sauvegarder une recherche, la réappliquer, activer/désactiver l'alerte puis vérifier son cloisonnement à l'entreprise.
3. Glisser une candidature d'une colonne ATS à une autre et vérifier l'historique.
4. Soumettre un dossier légal entreprise, le valider avec un administrateur, puis vérifier le badge public.
5. Modifier ensuite la raison sociale ou le nom/pays de l'entreprise et vérifier que la vérification est révoquée.
6. Vérifier que le justificatif n'est pas accessible directement sous `/media/employers/verification/...` en environnement nginx.
