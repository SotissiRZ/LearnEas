# Validation V92

## Contrôles effectués avant packaging

- suite structurelle frontend : **109/109 tests réussis** ;
- audit mobile : **136 fichiers inspectés, aucune alerte bloquante** ;
- `python -m compileall -q backend` : OK ;
- syntaxe Python des nouvelles migrations, tâches, services et commande : OK ;
- syntaxe TypeScript/TSX ciblée vérifiée avec le compilateur TypeScript global ;
- le code V92 ne stocke aucun numéro de carte/CVV/token de paiement réutilisable ;
- `automatic_charge` reste explicitement `false` avec les fournisseurs actuels ;
- remboursement Premium : inversion par ledger, pas suppression de l'historique ;
- achats unitaires : règles existantes inchangées.

L'environnement de génération ne contient pas Django ni `node_modules`. Le `makemigrations --check`, les tests Django et le `tsc --noEmit` complet doivent donc être exécutés dans Docker.

## Gates Docker

```bash
docker compose -f docker-compose.dev.yml exec backend python manage.py migrate
docker compose -f docker-compose.dev.yml exec backend python manage.py check
docker compose -f docker-compose.dev.yml exec backend python manage.py makemigrations --check --dry-run
docker compose -f docker-compose.dev.yml exec backend python manage.py test apps.payments apps.accounts apps.common

docker compose -f docker-compose.dev.yml exec frontend npm run test:ci
docker compose -f docker-compose.dev.yml exec frontend npm run build:check
```

## Contrôle V92

```bash
docker compose -f docker-compose.dev.yml exec backend python manage.py premium_revenue_report --json
```

Avant production, vérifier explicitement le pourcentage `Pool Premium créateurs (%)` dans l'administration. La valeur par défaut de 60 % est une configuration produit, pas une recommandation fiscale ou contractuelle.
