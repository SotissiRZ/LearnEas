# Validation V93 — Production Go-Live

## Contrôles exécutés dans l'environnement de génération

- tests structurels frontend : **118/118 OK** ;
- audit mobile : **136 fichiers, aucune alerte bloquante** ;
- préflight frontend avec URLs HTTPS factices : **OK** ;
- compilation syntaxique Python (`compileall`) : **OK** ;
- syntaxe Node des scripts V93 et `next.config.js` : **OK** ;
- YAML : `docker-compose.dev.yml`, `docker-compose.yml`, `.github/workflows/ci.yml` : **OK** ;
- scan secrets haute confiance : **OK**.

## Contrôle non exécutable ici

Django n'est pas installé dans l'environnement de génération. Les commandes runtime suivantes doivent être exécutées dans le conteneur Docker utilisateur :

```bash
python manage.py migrate
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test apps.common apps.payments apps.accounts apps.formations
python manage.py production_preflight --json
```

Le `production_preflight` réel doit être exécuté seulement avec les vraies variables staging/production ; il est normal qu'il échoue tant que S3/R2, email, paiement, TURN ou ClamAV ne sont pas configurés.

## Correctif V93.1 — PostgreSQL / Premium renewal

Le test Docker utilisateur a révélé deux erreurs identiques dans `LearnerPremiumV92Tests` : PostgreSQL refuse `FOR UPDATE` sur la partie nullable de la jointure vers `last_order`.

Correction : verrouillage de `PremiumRenewalProfile` sans jointure nullable, puis verrouillage séparé de `Order` si `last_order_id` existe.

Validation locale après correctif :
- tests structurels : 116/116 ;
- audit mobile : 136 fichiers, aucune alerte bloquante ;
- parse Python AST : 299 fichiers ;
- aucune migration ajoutée.

Gate Docker restant : relancer `python manage.py test apps.common apps.payments apps.accounts apps.formations`, puis les gates frontend.
- Pagination `InteractiveFormationViewSet` rendue déterministe (`-created_at`, `-id`) pour supprimer l'avertissement DRF/Django observé dans le même run.
## Correctif V93.2 — récupération checkout Premium

Le second run Docker utilisateur a confirmé que le correctif PostgreSQL V93.1 fonctionne : une seule erreur restait sur 109 tests, causée par un nom d’argument incorrect lors de la reconstruction d’un checkout Premium incomplet.

Correction : `mark_attempt_redirected(order, reference=order.provider_reference)` conformément à la signature réelle du helper de lifecycle.

Validation locale après correctif :
- tests structurels : 117/117 ;
- audit mobile : aucune alerte bloquante ;
- parse/compile Python : OK ;
- aucune migration ajoutée.

Gate Docker restant : relancer `python manage.py test apps.common apps.payments apps.accounts apps.formations`.
## V93.3 — Correctif harness Docker

- Cause observée dans Docker : les tests V91/V93 lisaient `/workspace/backend/docker/start-web.sh` et `/workspace/.env.production.example`, mais ces contrats de déploiement n'étaient pas montés dans le conteneur frontend.
- Correction : mounts explicites `:ro` pour `backend/docker/`, `docs/V93_GO_LIVE.md` et `.env.production.example`.
- Le dépôt complet et les `.env` runtime ne sont pas montés.
- Test structurel ajouté pour verrouiller la présence de ces mounts.
- Validation locale : 118/118 tests structurels et audit mobile sans alerte.
- Validation Docker attendue : `npm run test:ci` doit désormais franchir `test:unit` puis poursuivre `audit:mobile` et `typecheck`.


## V93.4 — Correctif release:qualify:dev

Le run Docker V93.3 a validé le backend (109/109), `test:ci` frontend (118/118), audit mobile, typecheck et build production. Le dernier gate `release:qualify:dev` révélait des 308 causés par la normalisation `trailingSlash=false` de Next avant rewrite, ainsi que des timeouts de compilation initiale en `next dev`.

Correction :
- URLs same-origin `/api/...` slashless ;
- slash Django maintenu uniquement sur la destination upstream / backend direct ;
- warm-up local des pages ;
- timeouts/seuils de charge local-dev séparés des seuils release.

Aucune migration ni modification métier.
