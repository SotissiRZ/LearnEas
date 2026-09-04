# KalanPro v59 — partage d'écran sans quitter la réunion

## Objectif

Le partage d'écran ne force plus une disposition unique. Chaque participant conserve le contrôle de sa propre vue.

## Comportement

- En mode `Auto`, si plusieurs participants sont présents, le partage reste dans la vue réunion/galerie.
- `Agrandir le partage` place le partage actif sur la scène principale.
- `Revenir à la réunion` restaure la galerie sans arrêter le partage.
- Les autres participants restent disponibles en vignettes lorsque le partage est agrandi.
- `Plein écran` agrandit la scène complète et reste indépendant du focus du partage.
- L'état début/fin de partage est signalé aux autres clients via `screen_share_state`.
- Cette action ne donne aucun droit de modération : `mute`, `camera_off` et `remove` restent réservés à l'organisateur.

## Architecture média

Le flux partagé existant reste composite pour préserver la compatibilité WebRTC actuelle : écran + caméra présentateur. La v59 ajoute une signalisation d'état séparée afin que le rendu soit contrôlé localement par chaque participant.
