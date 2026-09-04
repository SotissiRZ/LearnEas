# KalanPro AI — Phase 2, lot 1 (v63)

La v63 transforme KalanPro AI en copilote capable d'interroger les données structurées de la plateforme et de proposer des actions sûres.

## Outils de lecture

KalanPro AI peut demander au backend de :

- rechercher des cours, PDF et cohortes (`search_learning_catalog`) ;
- lire la progression du compte (`get_my_progress`) ;
- lire les certificats actifs (`get_my_certificates`) ;
- rechercher les opportunités et calculer le score de correspondance (`search_opportunities`) ;
- lister les contenus de l'instructeur (`get_my_instructor_content`).

Les outils lisent uniquement les données auxquelles l'utilisateur authentifié a accès. Ils ne dépendent pas du RAG plein texte et évitent au modèle d'inventer des prix, titres, scores ou états de progression.

## Actions avec confirmation obligatoire

Aucune mutation n'est exécutée au moment où le modèle la demande. Le backend crée d'abord une proposition `AIActionLog` avec un jeton de confirmation court et une expiration de 20 minutes.

Actions disponibles dans ce lot :

- ajouter un cours publié à la liste de souhaits ;
- enregistrer un quiz généré comme brouillon IA privé ;
- enregistrer un plan de cours comme brouillon IA privé.

L'utilisateur voit une carte `Confirmer / Refuser` dans la conversation. L'exécution ne se produit qu'après un POST authentifié sur le jeton appartenant au même utilisateur.

## Brouillons pédagogiques

Les quiz et plans sont stockés dans `AIDraft`. Ils ne créent ni ne publient automatiquement un cours réel. L'instructeur peut les retrouver dans :

`/assistant/drafts`

## Journal administrateur

Le dashboard `Assistant IA` affiche les actions à confirmer, exécutées, échouées, le nombre de brouillons et les dix dernières actions. Le Django Admin conserve le journal complet.

## Compatibilité fournisseur

Le backend utilise le format `tools/function calling` de l'API Chat Completions compatible. Si le fournisseur configuré refuse ce format, KalanPro réessaie la requête sans outils afin que le chat classique reste disponible.

## Sécurité

- validation serveur stricte de tous les arguments ;
- contrôle de propriété pour les brouillons instructeur ;
- action accessible uniquement au propriétaire du jeton ;
- expiration des confirmations ;
- aucune publication automatique ;
- aucune candidature, paiement ou suppression automatique dans ce lot ;
- journal de chaque mutation proposée/exécutée/refusée.

## Étape suivante

Le lot suivant de Phase 2 pourra ajouter : candidature assistée avec écran de confirmation, création réelle d'un cours brouillon à partir d'un `AIDraft`, analyse CV/offre plus détaillée, et outils mentor/recruteur.
