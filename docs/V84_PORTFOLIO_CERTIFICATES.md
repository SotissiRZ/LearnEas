# KalanPro v84 — Portfolio & certificats avancés

## Portfolio professionnel

v84 transforme le portfolio en preuve professionnelle structurée. Chaque réalisation peut désormais décrire :

- le rôle du candidat ;
- le problème / contexte ;
- l’objectif ;
- le résultat / impact ;
- la stack / les outils ;
- les compétences ;
- une vidéo de démonstration ;
- les dates de début et de fin ;
- le lien public et le dépôt source.

Les preuves KalanPro issues d’un projet validé restent immuables. L’apprenant peut modifier la présentation riche, la couverture et la visibilité, mais ne peut pas falsifier le cours, le projet, l’instructeur ou la note vérifiés.

## Confidentialité

Le pays, les notes de projet, l’email de contact et les certificats publics sont contrôlés séparément. L’email du compte n’est jamais utilisé implicitement : un email public dédié doit être saisi puis explicitement activé.

Les certificats sont ajoutés au portfolio par sélection explicite. Un certificat sélectionné qui devient révoqué ou expiré n’est plus présenté comme certificat actif sur la page publique.

## Certificats

Le registre existant conserve QR, UUID, numéro unique, révocation, expiration, réémission et empreinte SHA-256. v84 ajoute :

- un PDF généré côté serveur avec QR de vérification ;
- un filigrane `RÉVOQUÉ` ou `EXPIRÉ` pour les anciennes preuves ;
- une URL PDF exposée par l’API ;
- une entrée CV structurée (titre, émetteur, dates, identifiant, URL de vérification, compétences) ;
- un bouton frontend « Copier pour mon CV » ;
- l’affichage contrôlé des certificats actifs sur le portfolio public.

## Migrations

- `projects.0002_portfolio_evidence_v84`

Migration additive uniquement : nouveaux champs portfolio et nouvelle table de sélection de certificats. Aucune donnée existante n’est supprimée.
