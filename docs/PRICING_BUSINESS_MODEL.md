# KalanPro — Modèle économique et grille tarifaire de lancement (v56)

## Principes

KalanPro conserve un accès **sans abonnement obligatoire pour les apprenants**. L'objectif est de rester compatible avec des usages Mobile Money et des budgets irréguliers : l'apprenant paie un cours, un PDF, une cohorte ou une séance de mentorat lorsqu'il en a besoin.

Les revenus de la plateforme sont diversifiés autour de trois sources :

1. **Commission marketplace** sur les ventes de contenus et les séances de mentorat.
2. **Offre Pro instructeur** à abonnement mensuel avec commission réduite.
3. **Recrutement B2B** : annonce ponctuelle et forfaits mensuels Pro / Business.

Tous les montants commerciaux sont stockés en **EUR**, devise comptable de base du projet, puis convertis avec le système de devises existant. Les taux XOF/XAF peuvent donc être affichés dans la navbar sans dupliquer la logique de prix.

## Tarifs par profil

### Apprenant

- Compte : gratuit.
- Aucun abonnement mensuel obligatoire.
- Cours, PDF et cohortes : prix fixé au niveau du contenu.
- Mentorat : prix fixé par le mentor et payé à la séance / réservation.
- Certificat : inclus lorsqu'il est prévu par le contenu et que les critères sont remplis.

### Instructeur

**Standard**
- 0 EUR / mois.
- Commission plateforme par défaut : 15 % (champ existant `platform_commission_percent`).

**Pro créateur**
- Prix de lancement par défaut : 15,09 EUR / mois (environ 9 900 XOF au taux fixe CFA/euro).
- Commission cible : 8 %.
- Activation commerciale sur demande tant que l'abonnement récurrent n'est pas automatisé.

### Mentor

- 0 EUR / mois.
- Commission par défaut : 15 % sur la séance encaissée.
- Le taux `mentor_commission_percent` est désormais réellement utilisé lors de la création de la commande de mentorat.

### Entreprise / recruteur

- Starter : profil gratuit ; capacité commerciale de référence administrable.
- Annonce ponctuelle : 11,43 EUR / 30 jours (environ 7 500 XOF).
- Pro : 30,34 EUR / mois (environ 19 900 XOF), 5 offres actives par défaut.
- Business : 76,07 EUR / mois (environ 49 900 XOF), 20 offres actives par défaut.

Depuis la v78, les offres recruteur sont achetables en self-service via le checkout KalanPro. Chaque achat crée un droit (`entitlement`) rattaché à sa commande : annonce à l’unité, Pro ou Business. Les périodes Pro/Business durent 30 jours et les achats successifs sont chaînés ; les droits sont révoqués ou recalés lors d’un remboursement.

## Administration

Les paramètres sont accessibles dans **Administration → Paramètres → Modèle économique & tarifs publics** :

- affichage de la page Tarifs ;
- prix Pro instructeur ;
- commission Pro instructeur ;
- commission mentor ;
- quota recruteur gratuit ;
- prix annonce à l'unité ;
- prix/quota recruteur Pro ;
- prix/quota recruteur Business.

La route publique `/api/auth/platform-settings/` expose uniquement les paramètres nécessaires à l'affichage de la grille tarifaire.

## Étape suivante recommandée

Le module d’entitlements recruteur est disponible depuis la v78 : statut payé, périodes de 30 jours, enchaînement des renouvellements, révocation au remboursement, crédits d’annonce et limites d’offres actives. Une future évolution pourra ajouter une facturation récurrente automatique par mandat ; la v78 reste fondée sur des achats/renouvellements explicites via les passerelles existantes.
