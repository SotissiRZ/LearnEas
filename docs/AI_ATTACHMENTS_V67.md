# KalanPro AI — pièces jointes (v67)

## Formats pris en charge

- Documents : PDF, DOCX, TXT, CSV, Markdown, JSON, XLSX, PPTX.
- Images : PNG, JPEG/JPG, WebP.
- Les scans PDF purement image ne sont pas OCRisés dans cette version.
- Les images sont réellement transmises au modèle uniquement lorsque `AI_VISION_ENABLED=True` et que le fournisseur choisi accepte les entrées multimodales.

## Confidentialité et sécurité

Les fichiers sont liés au compte utilisateur et à la conversation. Les endpoints de téléchargement et suppression exigent l'authentification et vérifient la propriété du fichier.

La validation ne fait pas confiance au nom du fichier : taille, extension, signatures PDF/Office/ZIP, structure ZIP et protections anti archive expansive sont appliquées via la couche commune KalanPro. Les PDF et documents Office utilisent également le scanner malware existant lorsque celui-ci est exigé par la configuration de production. Les images sont décodées avec Pillow et limitées à 25 mégapixels.

Le contenu extrait est traité comme une donnée non fiable dans les prompts IA et ne peut pas remplacer les instructions système.

## Réglages administrateur

Dans `Dashboard admin → Assistant IA` :

- activation des pièces jointes ;
- taille maximale par fichier (1 à 25 Mo) ;
- nombre maximal de fichiers par message (1 à 8) ;
- longueur maximale de texte extrait par fichier.

## Variables serveur

```env
AI_VISION_ENABLED=False
```

Laisser `False` si le modèle n'accepte pas les images. Le chat texte et les documents restent fonctionnels.

## API

- `POST /api/ai/attachments/` — upload multipart ;
- `GET /api/ai/attachments/<id>/download/` — téléchargement privé ;
- `DELETE /api/ai/attachments/<id>/` — suppression ;
- `POST /api/ai/chat/` avec `attachment_ids: [1, 2, ...]` — associer les fichiers au message.

## Exports carrière

Les brouillons IA privés peuvent être exportés depuis `Mes brouillons IA` :

- PDF ;
- DOCX (Word).

Les exports concernent notamment CV amélioré, lettre de motivation, plan de compétences et préparation d'entretien.
