# WhatsApp transactionnel — KalanPro v82

KalanPro utilise **Meta WhatsApp Cloud API** directement. Aucun token Meta n'est exposé au frontend.

## 1. Flux implémentés

Les messages business-initiated sont envoyés avec des **templates approuvés** :

| Événement | Template par défaut | Variables BODY, dans l'ordre |
| --- | --- | --- |
| Paiement confirmé | `kalanpro_payment_confirmed` | `{{1}}` prénom/nom, `{{2}}` n° commande, `{{3}}` montant + devise |
| Rappel live / mentorat | `kalanpro_live_reminder` | `{{1}}` prénom/nom, `{{2}}` formation/séance, `{{3}}` date/heure, `{{4}}` URL de la salle |
| Reprise après inactivité | `kalanpro_inactivity_reminder` | `{{1}}` prénom/nom, `{{2}}` cours, `{{3}}` progression, `{{4}}` URL du cours |
| Certificat disponible | `kalanpro_certificate_ready` | `{{1}}` prénom/nom, `{{2}}` contenu, `{{3}}` URL de vérification |
| Recrutement | `kalanpro_recruitment_update` | `{{1}}` prénom/nom, `{{2}}` opportunité, `{{3}}` détail événement, `{{4}}` URL KalanPro |
| Test administrateur | `hello_world` | aucune |

Les noms des templates KalanPro sont modifiables dans **Administration → Paramètres → WhatsApp transactionnel**.

## 2. Consentement utilisateur

Un message n'est planifié que si l'utilisateur :

1. renseigne un numéro au format E.164 (`+221...`, `+225...`, `+237...`) ;
2. active explicitement « Activer WhatsApp » ;
3. conserve activée la catégorie de notification correspondante.

La date du consentement est enregistrée. Le retrait du consentement bloque immédiatement les nouveaux envois.

## 3. Test local sans Meta

Dans `.env` :

```env
WHATSAPP_ENABLED=True
WHATSAPP_DRY_RUN=True
```

Puis activez aussi **WhatsApp** dans les paramètres administrateur. Les messages passent par Celery, sont journalisés avec le statut `simulated`, mais aucun appel externe n'est effectué.

```bash
docker compose down
docker compose up --build -d
docker compose exec backend python manage.py migrate
```

Le service `celery_beat` exécute les rappels live et recrutement toutes les 5 minutes et les relances d'inactivité une fois par jour. En v82, Docker dev inclut également `celery_worker` et `celery_beat`.

## 4. Production Meta WhatsApp Cloud API

Variables serveur uniquement :

```env
WHATSAPP_ENABLED=True
WHATSAPP_DRY_RUN=False
WHATSAPP_GRAPH_API_VERSION=v25.0
WHATSAPP_PHONE_NUMBER_ID=...
WHATSAPP_ACCESS_TOKEN=...
WHATSAPP_VERIFY_TOKEN=...
WHATSAPP_APP_SECRET=...
BACKEND_PUBLIC_URL=https://api.example.com
FRONTEND_URL=https://www.example.com
```

`WHATSAPP_GRAPH_API_VERSION` est configurable : utilisez la version Graph API encore supportée par votre application Meta au moment du déploiement.

Webhook à déclarer chez Meta :

```text
https://api.example.com/api/notifications/whatsapp/webhook/
```

Le GET de vérification compare `hub.verify_token` avec `WHATSAPP_VERIFY_TOKEN`. Les POST de production sont authentifiés avec `X-Hub-Signature-256` et `WHATSAPP_APP_SECRET`.

## 5. Railway

Le backend web, le worker Celery et Celery Beat doivent être des processus/services distincts partageant le même PostgreSQL et Redis :

```text
web     : gunicorn ...
worker  : celery -A learneas worker --loglevel=info
beat    : celery -A learneas beat --loglevel=info
```

Ne lancez qu'une seule instance de Celery Beat pour éviter plusieurs déclenchements périodiques. Les clés Meta doivent être configurées sur les services qui en ont besoin, en particulier le worker.

## 6. Idempotence

Chaque événement métier possède une `event_key` unique. Une répétition du webhook de paiement, d'un job planifié ou d'une réémission identique ne produit donc pas plusieurs messages identiques.

Le webhook Meta met à jour le journal d'envoi : `sent` → `delivered` → `read`, ou `failed`.
