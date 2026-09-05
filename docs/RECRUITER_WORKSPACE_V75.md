# KalanPro v75 — Recruiter Workspace, ATS & marque employeur

## Objectif

La v75 transforme l'ancien écran recruteur en véritable workspace de recrutement. Les données v73/v74 restent conservées ; la migration est additive.

## Marque employeur

Une entreprise peut configurer :

- logo ;
- bannière / cover ;
- couleur de marque ;
- accroche ;
- description ;
- secteur, taille et année de création ;
- site web et LinkedIn ;
- email recrutement ;
- valeurs ;
- avantages candidats ;
- zones de recrutement.

Une entreprise approuvée peut modifier le contenu et les médias de marque sans perdre son statut. Le nom et le pays restent des éléments d'identité sensibles et déclenchent une nouvelle validation.

## Page entreprise publique

`/companies/<slug>` affiche le branding de l'entreprise, ses informations principales, ses valeurs, ses avantages et ses offres actuellement ouvertes. Seules les entreprises `approved` sont exposées par l'API publique.

## Offres enrichies

Chaque opportunité peut maintenant contenir :

- un visuel / cover ;
- un département ou une équipe ;
- le nombre de postes ;
- les missions et exigences ;
- les compétences obligatoires et bonus ;
- jusqu'à huit questions de présélection ;
- la rémunération, le mode de travail, la localisation et la date limite.

Les réponses de présélection sont enregistrées avec la candidature afin de rester liées au dossier transmis au moment T.

## ATS / pipeline

Le recruteur dispose d'un pipeline visuel par étapes : nouvelle candidature, en étude, présélection, entretien, offre, recruté et non retenu.

Pour chaque candidature, le recruteur peut conserver :

- une note interne ;
- une notation de 1 à 5 ;
- des tags ;
- une prochaine étape datée ;
- le statut du pipeline.

Le CV transmis, le portfolio partagé et les certificats/projets vérifiés restent consultables depuis le dossier candidat.

## Vivier de talents

Le vivier reste strictement opt-in côté candidat. Les recruteurs approuvés peuvent filtrer par texte, pays, disponibilité et expérience minimale, puis enregistrer des talents en favoris persistants.

## Analytics

`GET /api/opportunities/employer-profile/analytics/` retourne les indicateurs principaux du recruteur : offres publiées/brouillons, candidatures, distribution du pipeline, entretiens, offres, recrutements, match moyen et talents favoris.

## API ajoutée / enrichie

- `GET /api/opportunities/companies/<slug>/`
- `GET /api/opportunities/employer-profile/analytics/`
- `GET/POST/PATCH/DELETE /api/opportunities/talent-bookmarks/`
- `Opportunity` : `cover_image`, `department`, `openings`, `screening_questions`
- `OpportunityApplication` : `screening_answers`, `recruiter_rating`, `recruiter_tags`, `next_step_at`
- `EmployerProfile` : champs de branding v75

## Migration

`opportunities.0003_recruiter_workspace` ajoute uniquement de nouveaux champs et la table `TalentBookmark`. Elle ne supprime ni offre, ni candidature, ni profil entreprise existant.
