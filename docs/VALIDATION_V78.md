# Validation KalanPro v78

## Périmètre

La v78 termine le lot Recruiter Workspace commencé en v75–v77 : confidentialité du vivier, gouvernance des accès, droits payés, quotas de publication, cycle remboursement/renouvellement, checkout employeur, entretiens/offres d’embauche et SEO des offres.

## Migrations additives

1. `payments.0013_employer_entitlement_code`
   - ajoute le type de ligne `employer`;
   - ajoute `OrderItem.entitlement_code` (`max_length=191`).
2. `opportunities.0004_employer_governance`
   - journal d’accès talent ;
   - droits employeur ;
   - rattachement offre ↔ crédit de publication ;
   - historique ATS ;
   - entretiens ;
   - offre d’embauche.
3. `formations.0011_rename_..._and_more`
   - synchronise les noms d’index calculés par Django ;
   - synchronise le `help_text` historique de `FormationSession.meeting_link` ;
   - aucune transformation de donnée métier.
4. `opportunities.0005_alter_opportunity_apply_mode`
   - synchronise le libellé du choix `internal` vers « Candidature KalanPro » ;
   - aucune transformation de donnée métier.

Aucune opération `DeleteModel`, `RemoveField` ou suppression de données n’est introduite par ces migrations.

## Invariants métier contrôlés

- Starter n’accède pas au vivier ; Pro/Business oui.
- Un opt-out candidat supprime les favoris persistants associés.
- Les preuves portfolio ne sont jamais sérialisées lorsque `share_portfolio=false`.
- Un crédit annonce ne peut être consommé qu’une fois et sa fenêtre maximale est de 30 jours.
- Le prix recruteur est déterminé par `PlatformSettings` côté backend, jamais par le navigateur.
- Le checkout affiche les quotas Pro/Business issus de `PlatformSettings` et non des valeurs codées en dur.
- Le payload de planification d’entretien est strictement aligné sur le serializer backend.
- `Idempotency-Key` est obligatoire pour un checkout recruteur ; un replay identique renvoie la même commande.
- Une commande remboursée ne conserve pas un droit employeur actif.
- Les renouvellements Pro/Business ne se chevauchent pas et un remboursement recale uniquement les périodes futures encore concernées ; rembourser tardivement une période déjà entièrement écoulée ne prolonge pas les suivantes.
- Historique, entretiens et offre d’embauche utilisent trois endpoints/états UI distincts ; les appels entretien/offre candidat sont déclenchés uniquement pour les dossiers ayant atteint les étapes concernées afin d’éviter un N+1 réseau mobile.
- Seul le candidat concerné peut accepter/refuser son offre d’embauche ; une candidature retirée, embauchée ou déjà rejetée ne peut pas recevoir une nouvelle offre.
- Le JSON-LD public utilise `JobPosting`, mappe les vrais contrats KalanPro (`fixed_term`, `permanent`, etc.) vers Schema.org et n’expose que les champs publics de l’offre.

## Contrôles exécutés hors Docker

- `python -m compileall -q backend`
- parsing AST de 187 fonctions de tests backend
- graphe de 65 migrations : aucun préfixe dupliqué, dépendance projet manquante ou cycle
- `node --test scripts/test-performance.mjs scripts/test-security.mjs scripts/test-employer-role.mjs`
  - résultat : **22/22 tests passés**
- `node scripts/audit-mobile.mjs`
  - résultat : **123 fichiers inspectés, aucune alerte bloquante**
- parsing TypeScript/TSX syntaxique des fichiers modifiés avec TypeScript 5.8

Le premier passage Docker réel a ensuite détecté et permis de corriger :

- le verrou PostgreSQL du mentorat sur une relation nullable (`FOR UPDATE` + `slot__session`) ;
- une barrière admin de paiement qui regardait `base_total_amount` au lieu du montant réellement facturé `total_amount` pour certaines commandes historiques ;
- deux fixtures de tests devenues obsolètes (cohorte publiée encore en `draft`, gateways déjà précréées par migration) ;
- l’attente sécurité d’une candidature étrangère, désormais volontairement masquée en `404` ;
- une erreur TypeScript `unknown` → `ReactNode` dans `assistant/drafts` ;
- les deux migrations de state Django `formations.0011` et `opportunities.0005`.

L’environnement de fabrication de l’archive ne contient toujours ni Django ni les `node_modules` complets du frontend. Le **second passage** des tests Django et du build Next doit donc être rejoué dans les conteneurs du projet avant de qualifier v78 de stable.

## Commandes de validation Docker

```bash
docker compose -f docker-compose.dev.yml up --build
docker compose -f docker-compose.dev.yml exec backend python manage.py migrate
docker compose -f docker-compose.dev.yml exec backend python manage.py check
docker compose -f docker-compose.dev.yml exec backend python manage.py makemigrations --check --dry-run
docker compose -f docker-compose.dev.yml exec backend python manage.py test apps.opportunities apps.payments
docker compose -f docker-compose.dev.yml exec frontend npm run build
```

Ne pas utiliser `docker compose ... down -v` pour cette mise à jour : aucune remise à zéro de PostgreSQL n’est requise.



## Validation Docker frontend sans collision

Quand `next dev` tourne dans le service `frontend`, utiliser `npm run build:check` et non `npm run build`. Le script construit dans `.next-build-check`, tandis que le serveur dev utilise `/app/.next` monté dans un volume Docker dédié.

## Correctif runtime multipart — profil entreprise

- Les serializers opportunities n'utilisent plus `QueryDict.copy()` sur les requêtes multipart : cette méthode effectue un `deepcopy` incompatible avec `TemporaryUploadedFile` (`BufferedRandom`).
- Une copie superficielle `MultiValueDict` conserve les fichiers uploadés sans tentative de pickle.
- Le correctif couvre profil entreprise (logo/bannière), profil candidat (CV), offre (cover image) et candidature (CV).
- Test de régression ajouté avec deux vrais `TemporaryUploadedFile` PNG sur le profil entreprise.
