# Projets pratiques et portfolio — KalanPro v46

## Objectif

La couche `apps.projects` transforme une formation KalanPro en preuve de compétence : l'instructeur publie un projet, l'apprenant remet un travail, l'instructeur corrige, puis un travail validé peut être publié dans un portfolio professionnel.

Le flux cible est : **apprendre → pratiquer → faire corriger → prouver → partager**.

## Projets de cours

Un instructeur peut créer plusieurs projets par cours et configurer :

- brief et consignes ;
- objectifs et livrables ;
- compétences travaillées ;
- échéance relative à la date d'inscription ;
- barème et note minimale ;
- nombre de nouvelles remises ;
- ordre d'affichage ;
- publication ;
- caractère obligatoire ou non pour l'obtention du certificat.

Un projet ne peut pas devenir rétroactivement obligatoire si des certificats ont déjà été émis pour le cours.

## Remises apprenant

Une remise peut contenir :

- titre et résumé ;
- lien de démonstration ;
- dépôt Git ;
- fichier de travail ;
- image de couverture ;
- compétences associées.

Le fichier de travail est limité par `MAX_PROJECT_UPLOAD_MB` (50 Mo par défaut). Les extensions prévues sont PDF, Office, ZIP, TXT/CSV et images usuelles.

Chaque remise formelle crée une révision immuable afin de conserver l'historique des versions. Pendant une correction, la remise courante est verrouillée. Une nouvelle version n'est possible que si l'instructeur demande des changements ou rejette la remise, et si la politique du projet l'autorise.

## Correction

L'instructeur du cours ou l'administrateur peut :

- approuver ;
- demander des modifications ;
- rejeter ;
- attribuer une note ;
- rédiger un feedback.

Une approbation n'est possible que si la note atteint la note minimale définie sur le projet.

## Certificat et projets obligatoires

Lorsque `required_for_certificate=true`, le certificat n'est émis que lorsque :

1. le seuil de progression vidéo du cours est atteint ;
2. tous les projets obligatoires publiés ont une remise approuvée.

L'ajout ou la suppression d'une exigence recalcule l'état des inscriptions qui n'ont pas encore reçu de certificat. Un certificat déjà émis n'est jamais invalidé rétroactivement.

## Portfolio professionnel

Chaque apprenant dispose d'un profil portfolio avec :

- URL publique personnalisable ;
- titre professionnel et présentation ;
- liste de compétences ;
- site, LinkedIn et GitHub ;
- statut « ouvert aux opportunités » ;
- contrôle d'affichage du pays ;
- contrôle d'affichage des notes.

L'apprenant peut ajouter deux types de réalisations :

### Projet KalanPro vérifié

Un projet approuvé peut être publié avec un badge de vérification KalanPro. Les preuves suivantes sont copiées dans un snapshot serveur immuable :

- cours ;
- projet ;
- instructeur ;
- date de validation ;
- note ;
- barème de référence.

L'apprenant peut modifier la présentation publique (titre, description, couverture, visibilité, ordre), mais pas falsifier les preuves de validation.

### Projet externe

L'apprenant peut également ajouter manuellement une réalisation externe avec description, couverture, URL, dépôt et compétences. Ces éléments ne reçoivent pas le badge vérifié KalanPro.

## Confidentialité

Le portfolio est privé par défaut. Seuls les éléments explicitement publics apparaissent sur `/portfolio/<slug>`.

La réponse publique ne contient ni email ni téléphone. Le pays n'est affiché que si l'utilisateur l'autorise.

Les fichiers de remise et leurs révisions restent privés : Nginx bloque leur accès direct et KalanPro utilise le mécanisme de média protégé/signé existant. Les images de couverture destinées à une publication portfolio peuvent, elles, être servies comme médias de présentation.

## API principale

- `GET/POST /api/projects/assignments/`
- `GET/POST/PATCH /api/projects/submissions/`
- `POST /api/projects/submissions/<id>/submit/`
- `POST /api/projects/submissions/<id>/review/`
- `POST /api/projects/submissions/<id>/publish-portfolio/`
- `GET/PATCH /api/projects/portfolio-profile/me/`
- `GET/POST/PATCH/DELETE /api/projects/portfolio-items/`
- `GET /api/projects/portfolio/<slug>/` (public si le profil l'autorise)

## Test de démonstration

Après :

```bash
python manage.py seed_demo
```

le compte apprenant de démonstration `fatou@learneas.com` dispose d'un projet approuvé et d'un portfolio public de démonstration.

## Migration

```bash
python manage.py migrate
```

La migration initiale est `projects.0001_initial`.
