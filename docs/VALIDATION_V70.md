# Validation KalanPro v70

Validations exécutées lors de la génération :

- YAML : `docker-compose.dev.yml`, `docker-compose.yml`, workflow CI parsés avec succès.
- Invariants dev : PostgreSQL/Redis non publiés sur l'hôte, backend sur `db:5432` via `postgresql://`.
- `backend/docker/entrypoint.sh` : syntaxe Bash valide et Python embarqué parsable.
- Backend : 221 fichiers Python parsés sans erreur de syntaxe.
- Migrations : 58 nœuds, aucun cycle détecté statiquement.
- Frontend : tests statiques de sécurité 4/4.
- Frontend : audit mobile 119 fichiers, aucune alerte bloquante.
- `apiDownload` : une seule définition.
- Aucun marqueur de conflit Git détecté.

La validation Docker runtime complète doit être effectuée sur une machine disposant du daemon Docker. Commande de référence sous Windows :

```cmd
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml up --build
```
