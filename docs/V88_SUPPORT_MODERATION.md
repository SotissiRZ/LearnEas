# KalanPro V88 — Modération + support utilisateur

V88 introduit un flux de support et de sécurité intégré à KalanPro sans modifier les fondations V79–V87 sauf lorsqu'une régression est détectée par les tests.

## Support utilisateur

- Centre `/support` authentifié pour étudiants, instructeurs et employeurs.
- Tickets privés avec référence KalanPro, catégorie, priorité et statut.
- Conversation persistante utilisateur ↔ support.
- Fermeture volontaire par le demandeur ; statuts de traitement pilotés par l'administration.
- Assignation d'un ticket à un administrateur.
- Notifications in-app lors d'une réponse du support ou d'un changement de statut.
- La page Contact renvoie vers le vrai centre de support au lieu de simuler l'envoi d'un formulaire.

## Modération

- Signalements privés et structurés : cible, motif, détails et URL de contexte.
- Déduplication des signalements actifs lorsqu'un identifiant de cible est disponible.
- File admin avec gravité, statut, assignation, action prise et note de résolution.
- Journal immuable des changements de décision (`ModerationActionLog`).
- Notification du déclarant lorsqu'une décision est enregistrée.
- Liens « Signaler » ajoutés aux fiches cours et PDF.

## Sécurité / confidentialité

- Un utilisateur ne voit que ses tickets et ses propres signalements.
- Seuls les admins peuvent modifier les statuts, priorités de traitement et décisions de modération.
- Un demandeur ne peut ni s'assigner un ticket ni le créer dans un état terminal.
- Les URLs fournies dans un signalement sont limitées aux chemins relatifs KalanPro ou à `http(s)`.
- Aucun message de support n'est stocké dans les analytics produit.

## Migration

Migration additive : `support.0001_support_moderation`.
Elle crée uniquement les tables de support/modération et leurs index ; aucune table ou donnée existante n'est supprimée.
## Correctif de validation TypeScript

Après validation dans le Docker réel, V88 a aussi corrigé une régression de contrat TypeScript héritée du workspace recruteur :

- réexport stable des types opportunités depuis `@/types` ;
- alias `OpportunityWorkMode`, `OpportunityExperience`, `OpportunityStatus` et `JobApplicationStatus` ;
- contrat `EmployerJobApplication` pour les écrans recruteur existants ;
- paramètres de tarification recruteur réintégrés dans `PlatformSettings` ;
- typage explicite du `Set<string>` des codes pays prioritaires ;
- test structurel `test-type-contract-v88.mjs` ajouté à `test:unit`.

Ce correctif ne modifie ni les migrations V88 ni les règles métier support/modération.

