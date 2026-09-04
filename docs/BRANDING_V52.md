# KalanPro — identité visuelle v52

La v52 remplace l'identité publique LearnEas par **KalanPro** sans renommer le package Python interne `learneas`, afin de préserver les migrations, commandes Celery, volumes Docker et déploiements existants.

## Palette

- Navy principal : `#06152f`
- Orange KalanPro : `#ff641a`
- Bleu secondaire : `#3767db`
- Vert : réservé aux états de succès / opportunités
- Surfaces : blanc et gris bleuté léger

## Composants structurants

- Navigation globale navy, logo KalanPro, CTA orange.
- Accueil : hero orienté apprentissage → mentorat → carrière, cartes de valeur, catalogue, ressources et CTA final.
- Footer navy.
- Login/register rethémés.
- Sidebars instructeur/admin navy avec accent orange.
- Les classes `brand-*` Tailwind pointent désormais vers l'orange, ce qui harmonise les boutons, liens, badges et focus de l'ensemble de l'application.

## Migration des installations existantes

La migration `accounts.0007_kalanpro_branding` met à jour :

- `site_name` vers `KalanPro` si l'ancienne valeur est `LearnEas` ;
- identité juridique par défaut ;
- emails d'assistance/confidentialité par défaut ;
- couleur et préfixe par défaut des certificats ;
- emails des comptes de démonstration `@learneas.com` vers `@kalanpro.com` lorsqu'il n'y a pas de conflit.

Les noms techniques de base de données, réseau Docker et module Django `learneas` restent inchangés volontairement.
