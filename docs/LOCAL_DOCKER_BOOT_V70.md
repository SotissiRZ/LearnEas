# KalanPro v70 — Démarrage local Docker

## Problèmes corrigés

La v69 pouvait rencontrer deux défauts de diagnostic en développement :

1. PostgreSQL exposait `5432:5432`, ce qui entrait en conflit avec un PostgreSQL déjà présent sur Windows.
2. Le bootstrap backend utilisait Django pour tester la base et masquait le détail de `OperationalError`, rendant un échec réseau/authentification impossible à diagnostiquer correctement.

## Nouveau comportement

- PostgreSQL et Redis ne sont plus publiés sur l'hôte en mode dev.
- Le backend se connecte à PostgreSQL via `postgresql://learneas:learneas@db:5432/learneas`.
- Le bootstrap vérifie PostgreSQL directement avec psycopg2 + `SELECT 1`.
- Chaque échec affiche la cause réelle dans les logs, sans exposer le mot de passe.
- Le healthcheck PostgreSQL utilise TCP.

## Commandes Windows

```cmd
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml up --build
```

Puis ouvrir :

- frontend : http://localhost:3000
- backend : http://localhost:8000
- admin : http://localhost:8000/admin

Pour vérifier l'état :

```cmd
docker compose -f docker-compose.dev.yml ps
docker compose -f docker-compose.dev.yml logs -f backend frontend db redis
```

Pour ouvrir PostgreSQL sans publier le port 5432 :

```cmd
docker compose -f docker-compose.dev.yml exec db psql -U learneas -d learneas
```
