# KalanPro — Email transactionnel avec Resend

KalanPro utilise Resend comme canal email transactionnel en complément de WhatsApp.

## Architecture

- Les requêtes métier créent un `EmailDelivery` idempotent.
- Celery (`notifications`) effectue l'appel HTTP vers `POST https://api.resend.com/emails`.
- Une `Idempotency-Key` dérivée de l'événement évite les doubles emails pendant les retries.
- Tous les emails utilisent `notifications/email/transactional.html` et possèdent un fallback texte.
- La clé API n'est jamais stockée en base ni exposée au frontend.

## Variables d'environnement

```env
RESEND_ENABLED=True
RESEND_DRY_RUN=False
RESEND_API_KEY=re_xxxxxxxxx
RESEND_API_BASE=https://api.resend.com
RESEND_HTTP_TIMEOUT=15
```

En local, utilisez `RESEND_ENABLED=True` et `RESEND_DRY_RUN=True` pour valider le workflow sans envoi réel.

## Configuration admin

Dans **Administration → Paramètres → Email transactionnel · Resend** :

- Activer/désactiver le canal ;
- nom d'expéditeur ;
- adresse d'expédition ;
- Reply-To.

Le domaine de l'adresse d'expédition doit être vérifié dans Resend avant la production.

## Emails pris en charge

- bienvenue après inscription ;
- confirmation de paiement ;
- rappel de séance live / mentorat ;
- certificat disponible ;
- réinitialisation du mot de passe ;
- invitation à une séance ;
- relance de progression si l'utilisateur l'active ;
- email de diagnostic administrateur.

## Préférences utilisateur

L'utilisateur peut activer/désactiver séparément Email et WhatsApp. La relance d'inactivité par email est désactivée par défaut.
