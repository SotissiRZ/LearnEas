# KalanPro AI — Phase 2, lot 2 (v64)

La v64 étend les outils KalanPro AI aux parcours emploi, mentorat, recrutement et à la création réelle de cours brouillons. Le principe de sécurité reste inchangé : **une mutation préparée par l'IA n'est exécutée qu'après confirmation explicite de l'utilisateur**.

## Candidature assistée

KalanPro AI peut désormais :

- analyser le profil candidat face à une offre (`analyze_my_cv_against_opportunity`) ;
- réutiliser le score explicable KalanPro et détailler compétences requises présentes/manquantes ;
- lire un extrait du CV du compte lorsqu'il s'agit d'un PDF ou DOCX extractible ;
- préparer une candidature interne (`submit_opportunity_application`) avec lettre de motivation et choix de partage du portfolio.

La candidature est créée seulement après confirmation. Au moment du clic, le backend revérifie que l'offre est toujours ouverte, interne, publiée par une entreprise approuvée, qu'elle n'appartient pas au candidat et qu'aucune candidature n'existe déjà.

## Création réelle de cours brouillon

L'outil `create_course_draft` peut préparer un vrai cours KalanPro à partir d'un plan généré :

- titre, sous-titre, description ;
- niveau, langue et catégorie éventuelle ;
- objectifs, prérequis et public cible ;
- sections et leçons.

Après confirmation, le backend crée `Course`, `Section` et `Lesson` avec `published=False`. Aucun cours n'est publié automatiquement. Le résultat renvoie directement vers l'éditeur instructeur.

## Mentor

Un compte possédant des offres de mentorat obtient automatiquement les capacités mentor :

- `get_my_mentor_sessions` : prochaines réservations confirmées dont il est le mentor ;
- `save_mentorship_plan_draft` : plan privé de préparation, objectifs, agenda, questions et suivi.

Le plan est stocké dans `AIDraft` et n'est jamais envoyé automatiquement au mentoré.

## Recruteur

Un compte disposant d'un `EmployerProfile` approuvé obtient automatiquement les outils recruteur, même si son rôle principal n'est pas `admin` :

- `get_my_recruiter_applications` ;
- `analyze_candidate_application` ;
- `save_interview_rubric_draft` ;
- `update_application_stage`.

Pour limiter le risque décisionnel, l'assistant ne peut déplacer une candidature qu'aux étapes :

- en étude ;
- shortlist ;
- entretien.

Il ne peut pas, via l'IA, rejeter un candidat, l'embaucher ou générer une offre d'emploi. Ces décisions finales restent dans l'interface recruteur normale.

## Capacités cumulées

Le statut IA expose maintenant des capacités fonctionnelles indépendantes du rôle principal :

- `learner` ;
- `instructor` ;
- `mentor` ;
- `recruiter` ;
- `admin`.

Cela permet à KalanPro AI d'afficher les outils mentor/recruteur dès que les profils métier correspondants existent, même avant une refonte complète du modèle de rôles cumulables.

## Contexte des offres

Le widget reconnaît maintenant `/opportunities/<slug>`. Sur une fiche d'offre, l'ID, le titre et l'entreprise sont intégrés au contexte validé. Une demande comme « Analyse mon CV face à cette offre » peut donc appeler le bon outil sans que l'utilisateur recopie l'identifiant.

## Brouillons IA supplémentaires

`AIDraft.Kind` comprend désormais :

- `quiz` ;
- `course_outline` ;
- `mentor_plan` ;
- `interview_rubric`.

La page `/assistant/drafts` est accessible à tout utilisateur authentifié et adapte son affichage au type de brouillon.

## Mode développement

Avec `AI_DRY_RUN=True`, la v64 sait maintenant reconnaître certaines demandes liées au CV, au mentorat, au recrutement et peut préparer une candidature/shortlist de démonstration lorsqu'un identifiant ou un contexte d'offre est disponible. L'action reste soumise au même bouton de confirmation.

## Sécurité et confidentialité

- résultats d'outils, CV, offres, portfolios et notes sont explicitement traités comme **données non fiables** dans le prompt système ;
- l'assistant ignore toute instruction trouvée à l'intérieur d'un CV ou d'un document ;
- le recruteur ne lit que les candidatures appartenant à son entreprise approuvée ;
- le mentor ne lit que ses réservations ;
- les CV analysés appartiennent uniquement au compte connecté ;
- les confirmations expirent toujours après 20 minutes ;
- chaque action reste journalisée dans `AIActionLog`.

## Migration

`assistant_ai.0004_phase2_advanced_tools`
