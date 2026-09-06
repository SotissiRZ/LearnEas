# KalanPro v85 — ATS & recrutement avancé

## Objectif

v85 approfondit le module recruteur sans ouvrir un nouveau silo : le vivier devient exploitable contre une offre précise, le score devient explicable, les recherches peuvent être sauvegardées avec alertes, le pipeline ATS accepte le glisser-déposer et la vérification légale d'une entreprise est séparée de la simple approbation de son profil.

## Matching explicable

Le backend calcule le score ; le navigateur ne reçoit que le résultat et son explication. Le détail expose les composantes `skills`, `role`, `work_mode`, `location`, `kind` et `experience`, ainsi que les compétences requises correspondantes/manquantes et quelques points forts. Une offre utilisée pour le matching doit appartenir à l'entreprise du recruteur.

Le score reste indicatif : il ne prend jamais une décision de recrutement et n'est pas utilisé pour rejeter automatiquement un candidat.

## Recherches talents sauvegardées

Les plans recruteur disposant du vivier peuvent mémoriser recherche, pays, disponibilité, expérience minimale, offre de référence et score minimum. Les recherches sont privées par entreprise et un nom dupliqué est refusé proprement par l'API.

Une tâche Celery horaire recherche les profils devenus visibles ou mis à jour depuis le dernier passage. Le curseur est composé de `(updated_at, candidate_id)` afin qu'un lot de plus de 300 profils ou plusieurs mises à jour partageant le même timestamp ne fasse perdre aucun talent. Les alertes utilisent le centre KalanPro puis les canaux email/WhatsApp autorisés par les préférences existantes.

## ATS visuel

Les candidatures restent regroupées dans les étapes existantes : nouvelle, étude, présélection, entretien, offre, recruté et non retenu. Les cartes sont déplaçables par glisser-déposer sur desktop ; le sélecteur de statut demeure disponible comme alternative tactile/clavier. La mutation passe toujours par l'endpoint serveur `review`, qui conserve les protections sur candidatures retirées et états finaux.

## Vérification d'entreprise

L'approbation d'un compte recruteur et la vérification de l'identité légale sont deux états distincts. Le dossier comprend raison sociale, numéro d'immatriculation, pays d'immatriculation et justificatif. Le recruteur soumet le dossier ; seul un administrateur peut le valider ou le rejeter.

La page publique n'expose que le booléen `is_identity_verified`. Numéro d'immatriculation, note de contrôle et justificatif ne sont jamais exposés par le serializer public. En production nginx, `/media/employers/verification/` est bloqué ; le back-office ouvre le justificatif avec une URL privée signée de courte durée. Avec S3/R2, le stockage KalanPro conserve les URLs signées et les objets en cache privé.

Toute modification par le recruteur du nom/pays d'entreprise ou des informations légales révoque la vérification d'identité. Un changement du nom ou du pays continue en plus de replacer le profil entreprise dans le workflow d'approbation existant.

## Migration

`opportunities.0006_ats_v85` est additive : nouveaux champs de vérification légale et nouvelle table `SavedTalentSearch`. Aucune donnée ou table historique n'est supprimée.
