# KalanPro — Emplois, stages et missions (v48)

## Objectif

Fermer la boucle produit **apprendre → pratiquer → certifier → portfolio → travailler** avec un marché d'opportunités intégré à KalanPro et adapté à l'Afrique francophone.

## Côté candidat

- Profil candidat privé par défaut.
- Compétences, métiers recherchés, disponibilité, modes de travail et pays préférés.
- Pays choisis exclusivement dans le référentiel KalanPro ; aucune saisie libre de pays. La sélection multiple est utilisable au tactile et propose une recherche dans la liste.
- CV privé (PDF/DOC/DOCX) servi uniquement par un endpoint authentifié.
- Activation explicite du mode « visible par les recruteurs ».
- Matching explicable 0–100 basé principalement sur les compétences du profil, les projets vérifiés et les certificats actifs, puis le métier recherché, l'expérience et les préférences de lieu, mode de travail et type d'opportunité.
- Candidature interne avec lettre, CV facultatif et partage facultatif du portfolio.
- Snapshot des preuves au moment de la candidature : compétences, certificats actifs, projets KalanPro vérifiés et copie du CV transmis. Une modification ultérieure du CV de profil ne change pas une ancienne candidature.
- Suivi : envoyée, en étude, présélection, entretien, offre, retenu, non retenu, retirée.

## Côté recruteur

Le recruteur utilise désormais le rôle utilisateur de premier niveau `employer`. Il crée son compte via le parcours **Entreprise / Recruteur** et reçoit automatiquement un `EmployerProfile` en attente de validation.

1. Le recruteur renseigne l'entreprise.
2. Le pays est choisi dans la liste KalanPro.
3. L'administrateur approuve ou refuse la demande.
4. Une entreprise approuvée peut publier des emplois, stages, missions et offres freelance.
5. Elle peut consulter les candidatures et le vivier de talents qui ont explicitement activé leur visibilité.

Les coordonnées privées d'un candidat ne sont jamais exposées dans le vivier de talents. L'email n'est transmis qu'après une candidature volontaire.

## Opportunités

Champs principaux :

- type : emploi, stage, freelance, mission ;
- contrat ;
- mode : distance, hybride, sur site ;
- niveau d'expérience ;
- pays/ville ou télétravail mondial ;
- rémunération facultative ;
- compétences requises et bonus ;
- date limite ;
- candidature interne KalanPro ou lien externe ;
- statut brouillon / publiée / clôturée / archivée.

Une rémunération masquée par le recruteur n'est pas exposée dans l'API publique.

## Administration

Le back-office KalanPro ajoute l'onglet **Recrutement** :

- demandes recruteur ;
- approbation / refus / suspension ;
- contrôle des opportunités récentes ;
- suspension d'une entreprise : ses annonces publiées sont automatiquement clôturées.

Les mêmes objets restent disponibles dans l'administration Django.

## API principale

- `GET /api/opportunities/listings/`
- `GET /api/opportunities/listings/<slug>/`
- `GET /api/opportunities/listings/matches/`
- `GET/PATCH /api/opportunities/candidate-profile/`
- `PATCH /api/opportunities/candidate-profile/me/`
- `GET /api/opportunities/candidate-profile/resume/`
- `GET/POST /api/opportunities/applications/`
- `POST /api/opportunities/applications/<id>/withdraw/`
- `POST /api/opportunities/applications/<id>/review/`
- `GET /api/opportunities/applications/<id>/resume/`
- `GET/POST/PATCH /api/opportunities/employer-profile/`
- `POST /api/opportunities/employer-profile/<id>/approve/`
- `POST /api/opportunities/employer-profile/<id>/reject/`
- `POST /api/opportunities/employer-profile/<id>/suspend/`
- `GET /api/opportunities/talents/`

## Sécurité et vie privée

- CV et fichiers de candidature bloqués en accès direct Nginx ;
- fichiers servis par endpoint authentifié ;
- unicité SQL d'une candidature par candidat et opportunité ;
- verrou transactionnel lors de la candidature afin d'éviter les doubles soumissions concurrentes ;
- un recruteur ne peut pas candidater à sa propre annonce ;
- une candidature retirée par le candidat ne peut pas être réactivée par le recruteur ;
- vivier de talents opt-in uniquement ;
- entreprises obligatoirement approuvées ;
- snapshots des preuves pour éviter qu'une candidature historique change si le profil est modifié ensuite ;
- les opportunités possédant des candidatures doivent être clôturées/archivées plutôt que supprimées.

## Démonstration

Après `python manage.py seed_demo` :

- recruteur : `recruteur@kalanpro.com` / `recruiter1234` ;
- entreprise : **Demo Digital Africa** ;
- deux opportunités de démonstration ;
- Fatou possède un profil candidat visible et une candidature de démonstration.
