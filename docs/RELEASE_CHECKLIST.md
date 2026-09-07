# KalanPro — Checklist de release

## A. Avant merge

- [ ] changement documenté dans CHANGELOG ;
- [ ] migrations intentionnelles et revues ;
- [ ] aucun `.env`/secret ajouté ;
- [ ] tests backend ciblés ;
- [ ] `npm run test:ci` ;
- [ ] `npm run build:check` ;
- [ ] scan secrets ;
- [ ] documentation mise à jour si variable/commande/infrastructure change.

## B. Avant staging

Backend :

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test apps.common apps.payments apps.accounts apps.formations
```

Frontend :

```bash
npm run test:ci
npm run build:check
npm run production:preflight
```

- [ ] aucune migration inattendue ;
- [ ] backup si migration sensible ;
- [ ] variables staging vérifiées ;
- [ ] workers/Beat configurés ;
- [ ] S3/R2/ClamAV/TURN accessibles.

## C. Staging

```bash
python manage.py production_preflight --json
python manage.py release_gate --strict-infra --deploy --production --json
```

Puis :

```bash
RELEASE_BASE_URL=https://<staging-front> \
RELEASE_BACKEND_URL=https://<staging-back> \
npm run release:smoke:prod
```

Tests manuels :

- [ ] inscription/login/logout/refresh ;
- [ ] cours/PDF/portfolio/certificat ;
- [ ] upload média + HLS ;
- [ ] paiement sandbox/test ;
- [ ] Premium ;
- [ ] mentorat/cohorte ;
- [ ] recruteur/ATS ;
- [ ] notifications ;
- [ ] support/modération ;
- [ ] live/WebRTC/TURN.

## D. Avant production

- [ ] sauvegarde DB récente et vérifiée ;
- [ ] version/tag Git identifié ;
- [ ] fenêtre de déploiement choisie ;
- [ ] rollback cible identifié ;
- [ ] domaines/webhooks production prêts ;
- [ ] aucun flag dry-run/test actif ;
- [ ] `SEED_DEMO=False` ;
- [ ] `DEBUG=False` ;
- [ ] `TEST_PAYMENTS_ENABLED=False`.

## E. Après production

```bash
RELEASE_BASE_URL=https://<prod-front> \
RELEASE_BACKEND_URL=https://<prod-back> \
npm run release:smoke:prod
```

- [ ] `/api/health/live/` vert ;
- [ ] `/api/health/ready/` vert ;
- [ ] Admin → Santé plateforme vert ;
- [ ] queues Celery raisonnables ;
- [ ] paiement test autorisé selon procédure ;
- [ ] email transactionnel test ;
- [ ] webhook paiement reçu ;
- [ ] upload média/HLS ;
- [ ] logs sans nouvelle erreur récurrente.

## F. Rollback si échec

- [ ] frontend : rollback Vercel ;
- [ ] backend : déploiement Railway sain précédent ;
- [ ] ne pas inverser automatiquement migrations additives ;
- [ ] ne restaurer DB qu’en cas de nécessité réelle ;
- [ ] refaire smoke ;
- [ ] ouvrir postmortem si P0/P1.
