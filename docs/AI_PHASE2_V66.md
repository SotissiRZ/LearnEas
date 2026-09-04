# KalanPro AI — Phase 2 · Carrière (v66)

Ce lot ajoute le copilote carrière candidat sans supprimer le contrôle humain.

## Outils de lecture

- `analyze_my_cv_against_opportunity` : analyse profil/CV face à une offre.
- `recommend_learning_for_opportunity` : calcule les compétences requises manquantes et recherche de vrais cours/PDF/cohortes publiés KalanPro pour les combler.

## Actions avec confirmation obligatoire

- `save_cv_improvement_draft` : sauvegarde une proposition d'amélioration CV/profil sans modifier le profil ni le fichier CV.
- `save_cover_letter_draft` : sauvegarde une lettre de motivation privée ; aucune candidature n'est envoyée.
- `save_learning_gap_plan_draft` : sauvegarde un plan de montée en compétences lié à une offre.
- `save_candidate_interview_prep_draft` : sauvegarde pitch, questions probables, exemples STAR, questions à poser et checklist.

Les brouillons sont disponibles dans `/assistant/drafts`.

## Garde-fous

- L'offre ciblée doit être publiée et rattachée à une entreprise approuvée.
- Le candidat ne peut pas cibler sa propre offre.
- Aucune réécriture du fichier CV n'est faite automatiquement.
- Aucune lettre n'est envoyée sans l'action séparée de candidature et sa confirmation.
- Les recommandations de formation proviennent uniquement du catalogue KalanPro publié.
