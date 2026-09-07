# KalanPro V90 — Release Qualification, E2E, charge et résilience

V90 ne change pas les fonctionnalités métier. Elle transforme la qualification d'une version en un processus reproductible avant déploiement Railway/Vercel.

## 1. Gate backend

La commande suivante vérifie :

- Django system checks ;
- absence de migrations non appliquées ;
- PostgreSQL ;
- cache Redis ;
- stockage distant si `REQUIRE_REMOTE_MEDIA=True`.

```bash
python manage.py release_gate --json
```

Pour un environnement de staging/production :

```bash
python manage.py release_gate --strict-infra --deploy --json
```

`--strict-infra` ajoute le broker/workers Celery et le stockage. `--deploy` rend bloquants les avertissements des Django deployment checks.

## 2. Smoke/E2E HTTP réel

Depuis le conteneur frontend ou une machine pouvant joindre l'application :

```bash
npm run release:smoke
```

Le smoke vérifie réellement : frontend `/healthz`, backend live/ready via le proxy same-origin, paramètres publics, catalogues cours/PDF/opportunités, pages principales et headers CSP/nosniff.

En Docker dev, où `seed_demo` crée les utilisateurs de test :

```bash
npm run release:smoke:dev
```

Cela ajoute un login administrateur, `/auth/me/` et `/ops/health/`. Les identifiants peuvent être remplacés avec `RELEASE_SMOKE_EMAIL` et `RELEASE_SMOKE_PASSWORD`.

## 3. Résilience réseau

```bash
npm run release:chaos
```

Le runner place un proxy local devant la stack, injecte de façon déterministe des réponses 503 et des délais supérieurs au timeout client, puis vérifie que des GET idempotents réussissent avec un nombre de retry borné. Aucune requête d'écriture n'est rejouée automatiquement.

## 4. Charge bornée

```bash
npm run release:load
```

Valeurs par défaut :

- 180 requêtes ;
- concurrence 18 ;
- timeout 5 s ;
- p95 maximal 1 500 ms ;
- taux d'erreur maximal 1 %.

Variables disponibles : `RELEASE_LOAD_REQUESTS`, `RELEASE_LOAD_CONCURRENCY`, `RELEASE_LOAD_TIMEOUT_MS`, `RELEASE_LOAD_MAX_P95_MS`, `RELEASE_LOAD_MAX_ERROR_RATE`.

Ce runner n'est pas un benchmark de capacité maximale. Il constitue un gate de régression rapide et reproductible. Les tests de capacité lourds doivent être lancés sur staging avec des seuils adaptés.

## 5. Qualification complète Docker dev

```bash
npm run release:qualify:dev
```

Cette commande enchaîne smoke authentifié, chaos puis charge bornée.

## 6. CI

La CI V90 conserve les jobs backend/frontend et ajoute un job `integration` qui :

1. construit réellement la stack Docker dev ;
2. attend le liveness frontend ;
3. exécute `release:qualify:dev` ;
4. exécute le gate backend ;
5. publie les logs utiles en cas d'échec ;
6. détruit les conteneurs sans supprimer de volumes utilisateur locaux.

## Critères de sortie V90

Une version n'est candidate au déploiement que si :

- backend tests = verts ;
- frontend `test:ci` = vert ;
- build frontend = vert ;
- `release_gate` = vert ;
- smoke = vert ;
- chaos >= 90 % de succès final ;
- charge sous les seuils configurés ;
- aucune migration pendante.
