# KalanPro v83 — Cohortes et mentorat avancés

La v83 approfondit les deux parcours live existants sans créer un module parallèle : les cohortes gagnent une liste d'attente transactionnelle et le mentorat 1:1 gagne des packs, des disponibilités récurrentes et une reprogrammation sûre.

## Cohortes : liste d'attente et capacité réelle

Une cohorte pleine peut désormais accepter des demandes dans `FormationWaitlistEntry`. La file conserve son ordre chronologique et distingue `waiting`, `offered`, `joined`, `cancelled` et `expired`.

Lorsqu'une place se libère, KalanPro propose automatiquement la place à la plus ancienne personne en attente. La priorité est temporaire : `COHORT_WAITLIST_OFFER_HOURS=24` par défaut, borné côté serveur entre 1 et 72 heures. Une priorité expirée passe à `expired` et la personne suivante peut être servie. L'utilisateur expiré peut rejoindre de nouveau la file en une seule action.

Le calcul de capacité ne se limite plus aux inscriptions : il additionne les inscriptions actives, les réservations de siège liées à un checkout `pending` et les offres de liste d'attente encore valides. Une priorité qui a déjà créé sa réservation de checkout n'est pas comptée deux fois.

La file est rafraîchie après libération d'une réservation de paiement, après révocation/remboursement d'une inscription et par Celery Beat toutes les 15 minutes. L'instructeur/co-instructeur dispose aussi d'une vue opérationnelle de la file depuis son dashboard ; elle expose uniquement le profil public compact de l'apprenant, jamais son email.

## Mentorat : packs de séances

`MentorshipPack` permet à un mentor de commercialiser un nombre de séances à prix groupé. Les garde-fous API imposent 2 à 20 séances et une validité de 7 à 730 jours.

Le checkout accepte `mentorship_pack_ids`. Après paiement, KalanPro crée un `MentorshipPass` rattaché à la commande source. La délivrance est idempotente grâce à une contrainte unique conditionnelle sur `(user, pack, source_order)`. Le solde restant ne peut pas dépasser le total du pass.

Lors d'une réservation avec un pass, le pass est verrouillé transactionnellement et une séance est débitée. La réservation est confirmée immédiatement, sans nouveau paiement. Une annulation autorisée recrédite la séance. Un remboursement du pack révoque le pass et annule les rendez-vous futurs liés. Un rendez-vous payé avec un pass doit avoir lieu avant l'expiration du pass.

## Reprogrammation sûre

Une réservation confirmée peut être déplacée sur un autre créneau de la même offre sans second paiement. La reprogrammation :

- respecte le délai d'annulation/reprogrammation de l'offre ;
- vérifie que le nouveau créneau est actif et réservable ;
- refuse un créneau situé après l'expiration du pass éventuel ;
- révoque l'ancienne invitation de salle et crée/active la nouvelle ;
- conserve `rescheduled_at` et `reschedule_count` ;
- déclenche une notification KalanPro après commit.

KalanPro sérialise aussi les réservations d'un même mentor par verrou de ligne sur le compte mentor et refuse deux rendez-vous qui se chevauchent, même s'ils appartiennent à deux offres différentes. Le serializer des créneaux marque également ces plages concurrentes comme indisponibles dans l'interface avant le clic de réservation.

## Disponibilités récurrentes

`MentorshipAvailabilityRule` décrit un jour de semaine, une plage horaire, un intervalle et une période de validité. L'API génère des créneaux futurs et Celery les prolonge sur un horizon de 45 jours toutes les 12 heures.

Chaque créneau automatique conserve sa provenance via `MentorshipSlot.availability_rule`. Cela permet de désactiver les anciennes disponibilités libres lorsqu'une règle change, est désactivée ou lorsque l'offre n'est plus publiée. Les créneaux ayant déjà une réservation active sont conservés pour ne jamais casser un rendez-vous existant. Les créneaux manuels ne sont jamais modifiés par ce nettoyage.

Deux règles d'une même offre ne peuvent pas définir des plages horaires qui se chevauchent le même jour, ce qui évite qu'une règle désactivée retire une disponibilité encore revendiquée par une autre règle.

## Migrations

La v83 ajoute deux migrations additives :

- `formations.0012_cohort_waitlist_mentorship_ops` ;
- `payments.0015_mentorship_packs`.

Elles ajoutent tables, champs, index et contraintes. Aucune table ni donnée existante n'est supprimée.

## Tâches périodiques

- `apps.formations.tasks.refresh_cohort_waitlists` : toutes les 15 minutes ;
- `apps.formations.tasks.generate_recurring_mentorship_slots` : toutes les 12 heures.

Le worker périodique de mentorat inspecte également les règles désactivées/non publiées qui auraient encore des créneaux futurs actifs afin de nettoyer les disponibilités fantômes.

## Démarrage local et files Celery

En développement, Docker lance trois rôles asynchrones distincts : `celery_worker` (`default,notifications`), `celery_media_worker` (`media`) et `celery_beat`. Le worker média est indispensable aux transcodages HLS/offline introduits en v81. `COHORT_WAITLIST_OFFER_HOURS` est transmis au backend et au worker qui exécute les tâches de cohortes.
