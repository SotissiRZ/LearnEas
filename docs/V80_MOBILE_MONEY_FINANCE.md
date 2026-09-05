# KalanPro v80 — Mobile Money et gouvernance financière

## Objectif

La v80 transforme le paiement externe existant en un flux financier exploitable et auditable en production. Le cœur reste indépendant du prestataire, tandis que CinetPay conserve le rôle de connecteur Mobile Money déjà présent dans KalanPro.

Cette version ne remplace pas les comptes marchands ni les clés réelles du prestataire. Un paiement live ne peut être validé qu'après configuration des identifiants de production et tests sur le compte marchand choisi.

## Principes de sécurité

- Aucun droit n'est attribué sur la seule foi du navigateur ou d'un callback client.
- Le statut payé est accepté uniquement après vérification serveur du prestataire et cohérence de la référence, du montant et de la devise.
- Les webhooks sont journalisés de manière persistante et idempotente : un redémarrage de Redis ou du backend ne réactive pas un webhook déjà consommé.
- Les données d'audit sont expurgées des secrets et informations sensibles avant stockage.
- Une anomalie de montant/devise bloque l'attribution des droits et ouvre une anomalie financière critique.
- Une commande Mobile Money ancienne n'est pas automatiquement déclarée échouée : certains wallets peuvent confirmer tardivement. Elle est signalée comme `stale_pending` pour revue/réconciliation.

## Nouveaux objets financiers

### PaymentAttempt

Une tentative représente un passage réel vers un prestataire : création, redirection, vérifications, paiement, échec ou erreur réseau/prestataire.

### PaymentEvent

Journal persistant des événements de checkout, webhooks, confirmations, réconciliations et interventions administrateur. Les événements externes possèdent une clé d'idempotence persistante.

### PaymentIssue

Anomalie actionnable associée à une commande :

- `amount_mismatch`
- `currency_mismatch`
- `provider_error`
- `reference_mismatch`
- `stale_pending`
- `webhook_rejected`

Une anomalie peut être résolue depuis le back-office avec une note de résolution.

## État prestataire sur Order

Les commandes exposent désormais :

- `provider_status`
- `payment_method`
- `last_provider_check_at`
- `expires_at`

Ces données complètent le statut métier KalanPro (`pending`, `paid`, `failed`, `refunded`) sans le remplacer.

## Webhooks et confirmation

CinetPay, GeniusPay et Stripe utilisent désormais le même pipeline d'audit et de cohérence financière.

Pour un événement de paiement :

1. validation de signature / environnement ;
2. identification de la commande ;
3. journalisation persistante ;
4. vérification serveur lorsque requise ;
5. comparaison référence / utilisateur lorsque disponible ;
6. comparaison montant et devise ;
7. attribution des droits uniquement si l'état payé est cohérent ;
8. sinon ouverture d'une anomalie sans fulfillment.

## Réconciliation

La tâche périodique `apps.payments.tasks.reconcile_pending_payments` vérifie les commandes externes encore en attente.

La tâche `apps.payments.tasks.flag_stale_pending_payments` signale les commandes dépassant leur fenêtre normale sans les annuler automatiquement.

Commande manuelle :

```bash
python manage.py reconcile_payments
```

Pour ne faire que la revue des commandes anciennes :

```bash
python manage.py reconcile_payments --stale-only
```

Variables :

```env
PAYMENT_RECONCILIATION_MIN_AGE_SECONDS=120
PAYMENT_RECONCILIATION_BATCH_SIZE=100
PAYMENT_ORDER_EXPIRY_HOURS=24
PAYMENT_STALE_BATCH_SIZE=200
```

## Back-office finance

La fiche d'une commande expose maintenant :

- tentatives prestataire ;
- événements d'audit ;
- anomalies ouvertes/résolues ;
- statut prestataire ;
- moyen de paiement ;
- dernière vérification ;
- date d'expiration opérationnelle.

La liste des commandes peut être filtrée sur les anomalies et exportée en CSV.

## Retour Mobile Money

La page de retour client ne sollicite plus le prestataire en boucle. Elle :

1. effectue une première confirmation serveur ;
2. interroge principalement l'état interne KalanPro mis à jour par webhook ;
3. ne déclenche que quelques vérifications prestataire espacées ;
4. laisse la réconciliation de fond continuer si la confirmation du wallet prend du temps.

Ce comportement réduit les appels inutiles et fonctionne mieux sur connexion mobile instable.

## Configuration live restant à fournir hors code

Pour accepter réellement des paiements en production, il reste à renseigner les éléments fournis par le prestataire retenu : identifiants marchands, clés API/secrets, URLs webhook publiques et activation des moyens Mobile Money du compte marchand.

Ces éléments ne doivent jamais être commités dans Git.

## Validation Docker recommandée

```bash
docker compose -f docker-compose.dev.yml exec backend python manage.py migrate
docker compose -f docker-compose.dev.yml exec backend python manage.py check
docker compose -f docker-compose.dev.yml exec backend python manage.py makemigrations --check --dry-run
docker compose -f docker-compose.dev.yml exec backend python manage.py test
docker compose -f docker-compose.dev.yml exec frontend npm run test:ci
docker compose -f docker-compose.dev.yml exec frontend npm run build:check
docker compose -f docker-compose.dev.yml exec backend python manage.py reconcile_payments
```

Ne pas utiliser `down -v` pour appliquer la v80.
