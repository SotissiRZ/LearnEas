# Cohortes et mentorat 1:1 — LearnEas v45

## Cohortes live

Les formations live classiques sont désormais présentées comme des **cohortes**. Une cohorte peut définir :

- un nom de cohorte (ex. `Cohorte Octobre 2026`) ;
- un fuseau horaire IANA (ex. `Africa/Abidjan`) ;
- un nombre minimum et maximum de participants ;
- une date/heure de clôture des inscriptions ;
- un planning de séances LearnEas ;
- un export calendrier `.ics`.

Les nouvelles inscriptions sont bloquées lorsque la cohorte est complète, lorsque la date limite est passée ou dès que la cohorte a effectivement démarré. Le checkout conserve le verrouillage transactionnel des dernières places.

## Mentorat 1:1

Un instructeur peut créer une offre de mentorat avec :

- titre et description ;
- durée de 15 à 180 minutes ;
- prix comptable en EUR, affiché/payé dans la devise choisie par l'utilisateur ;
- langue et fuseau horaire ;
- délai minimum de réservation ;
- délai minimum d'annulation côté apprenant ;
- publication/brouillon ;
- créneaux de disponibilité.

Chaque créneau génère une séance live LearnEas privée. Le conteneur technique n'est jamais publié dans le catalogue des cohortes et les certificats y sont désactivés. Un apprenant confirmé reçoit une invitation uniquement pour la séance réservée.

## Cycle d'une réservation

```text
créneau disponible
      ↓
réservation
      ↓
pending_payment (si payant)
      ↓
checkout LearnEas / Mobile Money / carte
      ↓
confirmed
      ↓
salle vidéo privée
      ↓
completed
```

Une réservation payante est gardée 45 minutes avant démarrage du checkout. Une fois le checkout créé, le verrou est prolongé jusqu'à 2 heures afin de laisser le temps aux confirmations Mobile Money différées. La contrainte SQL empêche deux réservations actives sur le même créneau.

Dès qu'une commande externe est créée, le créneau reste verrouillé tant que le prestataire la considère `pending`, même si l'expiration locale affichée est dépassée. L'apprenant ne peut pas annuler le rendez-vous pendant cette phase : cela évite qu'un webhook Mobile Money confirme ensuite une réservation dont le créneau aurait déjà été revendu. Un échec prestataire terminal libère la réservation. Une commande déjà payée reste prioritaire même si sa confirmation arrive tardivement.

Une annulation d'une séance déjà payée ne déclenche **jamais** automatiquement un remboursement : la décision financière reste explicite et séparée du statut du rendez-vous. Les offres et créneaux ayant déjà un historique ne sont plus supprimables ; le mentor les dépublie ou les désactive pour conserver l'audit financier.

## WhatsApp

Le système v44 est réutilisé. Si WhatsApp est activé et que les utilisateurs ont donné leur consentement, un rappel est envoyé avant le rendez-vous au participant confirmé et au mentor. Le même template `learneas_live_reminder` est réutilisé.

## Pages principales

- Public : `/mentorship`
- Détail d'une offre : `/mentorship/[slug]`
- Apprenant : `/dashboard/student/mentorship`
- Instructeur : `/dashboard/instructor/mentorship`
- Cohortes : `/formations`

## API

- `GET/POST /api/mentorship/offerings/`
- `GET /api/mentorship/offerings/mine/`
- `GET/POST/PATCH/DELETE /api/mentorship/slots/`
- `GET/POST /api/mentorship/bookings/`
- `POST /api/mentorship/bookings/{id}/cancel/`
- `POST /api/mentorship/bookings/{id}/complete/`
- `GET /api/formations/{slug}/calendar/`

## Migrations

```bash
python manage.py migrate
```

Migrations v45 :

- `formations.0009_cohorts_and_mentorship`
- `payments.0011_mentorship_order_items`
