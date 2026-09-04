# Correctifs audit v51 — Realtime, CSP et tests frontend

## Objectif

La v51 traite trois risques encore ouverts après la v50 : la signalisation live par polling intensif, la CSP permissive imposée par le runner de code, et l'absence de garde-fous frontend/E2E. Elle retire aussi les secrets TURN du bundle navigateur.

## 1. Realtime WebSocket

- Django fonctionne en ASGI via Daphne.
- Django Channels utilise Redis avec `channels-redis`.
- `POST /api/sessions/<id>/realtime-ticket/` émet un ticket signé, court, lié à l'utilisateur et à la séance.
- Le navigateur ouvre `/ws/sessions/<id>/?ticket=...`.
- Le consumer vérifie le ticket, l'accès à la séance et l'origine WebSocket.
- Les signaux déjà validés par l'API DRF sont poussés vers le groupe du destinataire.
- Présence, fichiers et état de séance déclenchent également des événements realtime.
- Le poll entrant toutes les secondes a été supprimé.
- En cas de panne WebSocket, le client active temporairement un fallback HTTP toutes les 3 secondes et tente de se reconnecter avec backoff.
- Un GET de rattrapage est exécuté à l'ouverture du socket pour réduire le risque de perte pendant le handshake.

Le maillage média reste WebRTC P2P. Channels remplace la signalisation/polling, pas l'architecture vidéo ; une SFU reste recommandée pour de grandes classes.

## 2. TURN côté serveur

Variables backend :

```env
RTC_STUN_URL=stun:stun.l.google.com:19302
RTC_TURN_URL=turn:turn.example.com:3478?transport=udp
RTC_TURN_SECRET=
RTC_TURN_TTL_SECONDS=3600
RTC_TURN_USERNAME=
RTC_TURN_CREDENTIAL=
```

Avec `RTC_TURN_SECRET`, le backend fabrique un username expirant et un credential HMAC temporaire compatible avec le mécanisme de secret partagé coturn. Le navigateur reçoit uniquement les credentials temporaires via la réponse de salle. Les anciennes variables `NEXT_PUBLIC_RTC_*` sont supprimées.

## 3. Railway / Vercel

Backend Railway :

```env
REDIS_URL=redis://...
REALTIME_ALLOWED_ORIGINS=https://app.example.com,https://project.vercel.app
REALTIME_TICKET_MAX_AGE_SECONDS=60
RTC_TURN_URL=turn:turn.example.com:3478?transport=udp
RTC_TURN_SECRET=<secret partagé coturn>
RTC_TURN_TTL_SECONDS=3600
```

Frontend Vercel :

```env
API_PROXY_TARGET=https://backend-production.up.railway.app
NEXT_PUBLIC_API_URL=/api
NEXT_PUBLIC_WS_URL=wss://backend-production.up.railway.app/ws
```

`/api` reste same-origin grâce au proxy Next.js. Le WebSocket peut pointer directement vers Railway ; son `Origin` reste l'origine Vercel et doit être autorisée par `REALTIME_ALLOWED_ORIGINS`.

## 4. CSP et runner de code

La page principale reçoit une CSP par requête avec nonce :

- `script-src 'self' 'nonce-…' 'strict-dynamic'` en production ;
- pas de `unsafe-inline`, `unsafe-eval` ou `wasm-unsafe-eval` pour les scripts de l'application ;
- `unsafe-eval` est ajouté uniquement en développement afin de ne pas casser le tooling Next.js local ;
- `style-src 'unsafe-inline'` reste temporairement nécessaire aux styles calculés existants.
- Le header `X-Frame-Options` est `DENY` sur l’application et `SAMEORIGIN` uniquement sur le runner ; Nginx ne force plus un `DENY` global qui casserait cet isolement contrôlé.

Le code apprenant est déplacé sous `/code-runner/` :

- iframe `sandbox="allow-scripts"` sans `allow-same-origin` ;
- CSP dédiée et beaucoup plus étroite ;
- JavaScript dans un Blob Worker, timeout 10 s ;
- Python/Pyodide dans un Worker, timeout 20 s ;
- communication parent/runner par `postMessage` avec validation de la source et nonce applicatif ;
- HTML/CSS prévisualisés dans des iframes sans droit d'exécuter du JavaScript.

## 5. Tests ajoutés

Backend :

- ticket realtime court, utilisateur/séance scoppés ;
- livraison Channels au destinataire ;
- credentials TURN temporaires servis côté backend.

Frontend statique :

```bash
npm run test:security
```

Le script vérifie :

- CSP principale avec nonce/strict-dynamic ;
- runner sans `allow-same-origin` et sans `eval` dans la page live ;
- absence du poll signal permanent à 1 s ;
- absence de JWT LearnEas persisté en local/session storage.

E2E :

```bash
npx playwright test
```

Les smoke tests contrôlent les en-têtes CSP et le confinement du runner après un build Next.js.

## 6. Release gates

Dans l'environnement de génération de v51, les dépendances npm/pip ne peuvent pas être installées à cause du réseau. Les contrôles statiques sont exécutés localement, mais les commandes suivantes doivent être vertes dans la CI avant production :

```bash
cd backend
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate --noinput
python manage.py test

cd ../frontend
npm ci
npm run audit:mobile
npm run test:security
npm run build
npx playwright test
```

Puis :

```bash
docker compose config -q
docker compose up --build
```
