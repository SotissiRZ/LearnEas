# KalanPro v88 — Premium apprenant

v88 ajoute un **pass apprenant de 30 jours** donnant accès à un catalogue asynchrone explicitement sélectionné par l'administrateur, sans remplacer les achats à l'unité.

## Périmètre

- cours vidéo complets marqués `premium_included` ;
- PDF vendus seuls marqués `premium_included` ;
- prix et activation globale administrables dans **Admin → Paramètres** ;
- inclusion/exclusion d'un cours ou PDF administrable dans **Admin → Contenus** ;
- filtre `Inclus dans Premium` dans les catalogues cours et PDF ;
- carte Premium active dans le dashboard étudiant ;
- checkout dédié `learner_product=premium` avec `Idempotency-Key` obligatoire ;
- renouvellements manuels chaînés par périodes de 30 jours.

Les cohortes live et le mentorat restent volontairement hors Premium : leurs capacités, créneaux et règles financières continuent d'être gérés par leurs checkouts dédiés.

## Droits et expiration

Les achats à l'unité restent des droits permanents (`access_expires_at = NULL`). Un accès réclamé via Premium est temporaire et porte :

- `source_subscription` ;
- `access_expires_at` aligné sur la couverture Premium continue restante.

Le manager d'accès de `CourseEnrollment` et `PDFPurchase` masque automatiquement un droit Premium expiré. La progression et les traces historiques restent en base.

Un achat à l'unité d'un contenu déjà accessible via Premium convertit proprement le droit temporaire en droit permanent : la progression existante est conservée, `source_subscription` et `access_expires_at` sont supprimés, et la nouvelle commande devient la source du droit.

## Renouvellement et remboursement

Chaque commande Premium payée crée au plus une `LearnerSubscription` grâce au `OneToOneField` vers `Order`.

Si une couverture est déjà active ou future, la nouvelle période commence exactement à la fin de la dernière période non révoquée. Les replays de checkout/webhook ne prolongent donc jamais deux fois le pass.

Lorsqu'une commande Premium est remboursée :

1. sa période est révoquée ;
2. les périodes achetées après elle sont avancées de la durée retirée afin d'éviter un trou artificiel ;
3. les droits temporaires sont recalés sur la nouvelle fin de couverture ;
4. les achats permanents restent intacts.

## Gouvernance catalogue

`premium_included` est modifiable par un administrateur. Le serializer ignore ce champ lorsqu'un instructeur crée ou modifie son propre contenu : un créateur ne peut donc pas placer unilatéralement son contenu dans Premium.

L'inclusion de contenus tiers dans Premium doit rester liée aux accords commerciaux conclus avec leurs créateurs. v88 ne met pas en place de pool automatique de redistribution de l'abonnement.

## API

```text
GET  /api/payments/premium/
POST /api/payments/premium/          # { course_id } ou { pdf_id }
POST /api/payments/checkout/         # { learner_product: "premium", ... }
```

Filtres catalogue :

```text
GET /api/catalog/courses/?premium_included=true
GET /api/catalog/pdfs/?premium_included=true
```

## Migrations

```text
accounts.0012_learner_premium_pricing
catalog.0008_premium_catalog
payments.0016_learner_subscription
enrollments.0008_subscription_entitlements
```

Toutes sont additives. Aucun achat existant n'est converti ou supprimé.
