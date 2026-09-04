# KalanPro AI — Phase 2, v68

## Objectif

La v68 termine le lot entretien/recrutement de la Phase IA 2 avec trois principes :

1. l’IA aide à préparer et structurer ;
2. les scores sont recalculés côté serveur et restent des indicateurs ;
3. aucune décision RH finale ni aucun message externe n’est envoyé automatiquement.

## Simulation candidat

Quand l’utilisateur demande une simulation d’entretien, KalanPro AI doit poser une question à la fois, attendre la réponse puis donner un feedback bref. À la fin, il peut proposer d’enregistrer une évaluation privée.

Le score global est calculé côté KalanPro :

- pertinence : 30 % ;
- preuves / exemples : 25 % ;
- clarté : 20 % ;
- adéquation au poste : 15 % ;
- communication : 10 %.

Le modèle propose les sous-scores, mais le serveur les borne entre 0 et 100 et recalcule le total.

## Suivi post-entretien

Le candidat peut demander un message de remerciement ou de relance. Le brouillon contient :

- objet ;
- message ;
- fenêtre d’envoi recommandée ;
- prochaines actions.

Le brouillon n’est jamais envoyé automatiquement. Il est exportable en PDF ou Word depuis **Mes brouillons IA**.

## Scorecard recruteur

Le recruteur peut préparer une scorecard liée à une candidature qu’il possède. Chaque critère possède :

- nom ;
- poids ;
- score ;
- éléments factuels / preuves.

KalanPro normalise les poids et calcule un score global. La création de cette scorecard ne change jamais le statut de la candidature. Les décisions de rejet, offre et embauche restent hors du périmètre des actions IA.

## Pièces jointes

Les pièces jointes v67 restent disponibles pendant les simulations et analyses : PDF, DOCX, tableurs, présentations, texte et images compatibles vision. Leur contenu reste traité comme donnée non fiable vis-à-vis du prompt système.

## Migration

```bash
python manage.py migrate assistant_ai
```

Migration attendue : `0007_interview_copilot`.
