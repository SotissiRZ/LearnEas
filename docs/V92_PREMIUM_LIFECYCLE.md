# V92 — Cycle Premium et redistribution créateurs

## Objectif

V92 complète le pass KalanPro Premium sans modifier les achats unitaires. Une période Premium reste un droit temporaire de 30 jours, tandis qu'un cours/PDF acheté à l'unité reste permanent selon les règles existantes.

## Renouvellement

Le profil `PremiumRenewalProfile` mémorise uniquement une préférence de renouvellement, le fournisseur, la devise et l'état opérationnel. KalanPro **ne stocke ni numéro de carte, ni CVV, ni token wallet réutilisable**.

Avec les connecteurs actuels (Stripe en mode paiement, YouCanPay, GeniusPay, CinetPay), V92 prépare automatiquement un checkout hébergé avant l'échéance. L'apprenant doit confirmer ce checkout. L'API expose donc explicitement `automatic_charge=false` et `recurring_mode=checkout_confirmation_required`.

États : `scheduled`, `action_required`, `past_due`, `paused`, `cancelled`.

Variables :

```env
PREMIUM_RENEWAL_LEAD_HOURS=72
PREMIUM_RENEWAL_GRACE_HOURS=48
PREMIUM_RENEWAL_BATCH_SIZE=100
PREMIUM_SETTLEMENT_BATCH_SIZE=200
```

La fenêtre de grâce est une **fenêtre de rattrapage de paiement**, pas une prolongation gratuite de l'accès Premium. Une fois la couverture expirée, l'accès temporaire cesse. Pendant la grâce, le checkout peut encore être confirmé/recréé. Après la grâce, l'orchestration passe en `paused`; si l'utilisateur rachète Premium plus tard, sa préférence active peut être replanifiée.

## Usage Premium

`PremiumContentUsage` enregistre au plus une ligne par contenu distinct et par période. La V92 ne rémunère pas les clics répétés : un cours ou PDF distinct utilisé vaut une unité de poids. Cela limite les effets des reconnexions, rafraîchissements et clients bavards.

Les accès unitaires ne participent jamais à ce calcul.

## Pool créateurs

`learner_premium_creator_pool_percent` est administrable dans **Administration → Paramètres**. Valeur par défaut : **60 %**. Cette valeur doit être revue avant production selon la marge, la fiscalité et les contrats créateurs.

À la fin d'une période payée :

1. le montant comptable de la période est figé ;
2. le pool créateurs est calculé ;
3. les contenus distincts utilisés sont regroupés par instructeur ;
4. les centimes sont répartis de façon déterministe ;
5. une `PremiumRevenueAllocation` immuable est créée par instructeur ;
6. une écriture positive `premium` crédite le ledger instructeur.

Sans usage éligible, aucune allocation créateur n'est fabriquée et le montant reste revenu plateforme.

## Remboursement

Un remboursement postérieur au settlement ne supprime pas l'historique. V92 crée une écriture négative `premium_refund`, puis marque l'allocation comme inversée. Le solde disponible et les futurs versements restent donc auditables.

## Exploitation

```bash
python manage.py premium_revenue_report --json
python manage.py premium_revenue_report --fail-on-past-due
```

Le tableau **Administration → Santé plateforme** expose également :

- renouvellements Premium à confirmer ;
- renouvellements échus ;
- périodes expirées encore à répartir.

## Tâches périodiques

Celery Beat exécute :

- `apps.payments.tasks.prepare_premium_renewals` ;
- `apps.payments.tasks.settle_premium_revenue`.

Les deux traitements sont bornés par lot et conçus pour être idempotents.
