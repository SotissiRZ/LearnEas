# KalanPro v57 — Salle live et planning modifiable

## Disposition vidéo

La salle live propose trois dispositions :

- **Auto** (par défaut) : seul, l'utilisateur reste en petite vignette sur une scène d'attente ; à plusieurs, la salle passe en galerie ; pendant un partage d'écran local, l'écran devient la scène principale.
- **Galerie** : affiche les flux locaux et distants dans une grille responsive.
- **Intervenant** : privilégie l'organisateur comme flux principal et place les autres flux en vignettes. Pendant un partage d'écran local, l'écran partagé reste prioritaire.

La caméra du présentateur reste intégrée en PiP déplaçable pendant le partage d'écran.

## Planning instructeur

Depuis **Dashboard instructeur → Formations interactives → Planning** :

- création d'une séance avec numéro, date/heure et durée ;
- modification inline de la date/heure et de la durée d'une séance future ;
- durée autorisée : **15 à 480 minutes** ;
- verrouillage du planning dès que la séance a démarré, est terminée ou complétée ;
- suppression toujours soumise aux permissions organisateur/admin ;
- synchronisation automatique des dates `start_date` / `end_date` de la cohorte avec le planning réel.

Les mises à jour utilisent `PATCH /api/sessions/{id}/` et conservent les contrôles de permission existants.
