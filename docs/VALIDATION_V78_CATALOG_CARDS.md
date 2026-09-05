# Validation v78 — cartes catalogue

## Changements

- Largeur maximale commune des cartes : 22rem.
- Grille responsive auto-fit centrée pour éviter les cartes excessivement larges et les lignes incomplètes déséquilibrées.
- Opportunités / cours / formations : visuels 16:10.
- PDF : visuels 4:3.
- Portfolio : visuels 16:10.
- Opportunité détail : visuel 16:9 mobile, 16:8 à partir de `sm`.
- Fallback visuel d'entreprise lorsque l'offre n'a pas d'image de couverture.

## Contrôles

- 24/24 tests frontend statiques.
- Audit mobile : 123 fichiers, aucune alerte bloquante.
- Parsing TypeScript/TSX : 122 fichiers, aucune erreur de syntaxe.
- Backend inchangé fonctionnellement ; aucune migration ajoutée.
