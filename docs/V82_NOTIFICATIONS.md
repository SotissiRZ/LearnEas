# KalanPro v82 — Centre de notifications multicanal

## Objectif

Unifier les notifications transactionnelles KalanPro autour de trois canaux :

1. **Centre interne KalanPro** — toujours disponible sans fournisseur externe ;
2. **Email Resend** — selon les préférences utilisateur ;
3. **WhatsApp Cloud API** — uniquement avec consentement explicite et template Meta approuvé.

## Centre interne

Nouveau modèle `InAppNotification` : événement idempotent, catégorie, priorité, titre, contenu, action, métadonnées, date de lecture et date de création.

Endpoints privés :

- `GET /api/notifications/`
- `GET /api/notifications/unread-count/`
- `POST /api/notifications/<id>/read/`
- `POST /api/notifications/read-all/`
- `GET/PATCH /api/notifications/preferences/`

Le queryset est systématiquement filtré sur `request.user`.

## Interface

- cloche globale dans la navbar avec badge non lu ;
- aperçu des 8 derniers événements ;
- page `/notifications` avec filtres par catégorie et mode « non lues seulement » ;
- préférences multicanal sur la même page ;
- synchronisation locale du badge après lecture.

## Recrutement

Les événements suivants déclenchent une orchestration idempotente après commit DB :

- nouvelle candidature → recruteur ;
- changement d'étape ATS → candidat ;
- entretien planifié → candidat ;
- rappel entretien à environ 60 minutes → candidat ;
- offre d'embauche créée/mise à jour → candidat ;
- offre acceptée/refusée → recruteur.

Le helper `queue_recruitment_after_commit()` évite qu'un worker lise une donnée avant le commit de la transaction métier.

## WhatsApp

Nouveau template plateforme : `whatsapp_recruitment_template_name`, valeur par défaut `kalanpro_recruitment_update`.

Le template recrutement reçoit quatre variables BODY :

1. nom/prénom ;
2. intitulé d'opportunité ;
3. détail de l'événement ;
4. URL KalanPro.

Le canal reste conditionné à :

- `PlatformSettings.whatsapp_enabled=True` ;
- `WHATSAPP_ENABLED=True` ;
- consentement utilisateur `whatsapp_opt_in=True` ;
- préférence `whatsapp_recruitment_enabled=True`.

## Rappels fiables

Celery Beat exécute toutes les 5 minutes :

- rappels live/mentorat déjà existants ;
- nouveau rappel d'entretien recrutement à ~60 min.

Le centre interne est ajouté aux rappels live et aux relances d'apprentissage.

En développement, `docker-compose.dev.yml` lance désormais aussi `celery_worker` et `celery_beat`, afin que les tâches asynchrones soient réellement testables localement.

## Migrations

- `accounts.0011_whatsapp_recruitment_template`
- `notifications.0003_notification_center`

Elles sont additives uniquement.
