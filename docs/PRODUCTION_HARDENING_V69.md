# KalanPro v69 — Durcissement production

## Invariants désormais imposés

1. **Une intention de checkout = une commande** : le client peut envoyer `Idempotency-Key`; la même clé avec un panier différent est refusée en `409`.
2. **Une confirmation de paiement est rejouable** : `_fulfill` utilise un verrou DB et répare les droits/ledger manquants sans doubler les effets.
3. **Un remboursement ne détruit pas l'historique** : les inscriptions sont révoquées, pas supprimées; progression et certificats restent auditables.
4. **Le ledger est append-only** : vente positive, remboursement négatif, versement négatif. Un remboursement après versement peut rendre le solde ledger négatif; les ventes futures compensent ce solde avant un nouveau retrait.
5. **Les webhooks ne sont plus un point unique de défaillance** : Celery Beat réconcilie périodiquement les commandes externes en attente.
6. **Le quota IA est protégé contre la concurrence** : une seule requête IA active par utilisateur via Redis.
7. **Les fichiers live ne sont jamais interprétés par le navigateur depuis KalanPro** : validation à l'upload et téléchargement forcé en pièce jointe neutralisée.

## Migrations v69

- `payments.0012_payment_hardening_ledger`
- `formations.0010_revocable_entitlements`
- `enrollments.0006_revocable_entitlements_certificate_history`

Les migrations incluent une reprise des données existantes : ledger historique, rattachement des droits aux commandes payées/remboursées et révocation des droits/certificats issus d'anciens remboursements.

## Validation avant déploiement

```bash
# Backend
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate --noinput
python manage.py test

# Frontend
npm ci --no-audit --no-fund
npm run test:security
npm run audit:mobile
npx tsc --noEmit
npm run build
```

La CI `.github/workflows/ci.yml` exécute ces release gates automatiquement.
