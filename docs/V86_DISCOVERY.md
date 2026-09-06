# KalanPro v86 — Recherche globale & recommandations

## Objectif

v86 unifie la découverte de KalanPro sans introduire un moteur externe ni une nouvelle source de vérité. Les résultats sont construits à partir des modèles métier existants et respectent leurs règles de visibilité.

## Endpoints

- `GET /api/discovery/search/?q=<terme>&types=course,formation,...&limit=8`
- `GET /api/discovery/search/suggestions/?q=<terme>`
- `GET /api/discovery/recommendations/?limit=6`

Types supportés : `course`, `formation`, `pdf`, `mentor`, `opportunity`, `company`, `talent`.

## Confidentialité

La recherche anonyme/publique ne peut jamais retourner de talent. Les talents ne sont ajoutés aux types disponibles que pour un utilisateur `employer` :

1. disposant d'un `EmployerProfile` approuvé ;
2. disposant d'un droit actif Pro ou Business ;
3. consultant uniquement des `CandidateProfile.is_searchable=True`.

Les emails, CV et données privées ne sont pas inclus dans les résultats de découverte.

Les autres objets sont filtrés selon leur statut public : cours/PDF/mentorat/formations publiés, offres actuellement publiées et non expirées, entreprises approuvées.

## Classement

Le ranking combine :

- correspondance exacte du titre ;
- début de titre ;
- présence de la phrase ;
- correspondance tokenisée dans titre/description/champs métier ;
- boost contenu `featured` ;
- signaux de qualité déjà disponibles (note, étudiants/téléchargements) ;
- score de matching candidat/offre lorsqu'un profil candidat existe ;
- statut de vérification et nombre d'offres ouvertes pour les entreprises.

Les requêtes sont bornées à 120 caractères, les tokens à 8 et les jeux candidats sont plafonnés avant ranking Python afin de ne pas charger un catalogue entier en mémoire.

## Recommandations

Pour un utilisateur connecté, les signaux peuvent inclure :

- headline et domaine du compte ;
- pays ;
- compétences et rôles souhaités du profil candidat ;
- préférences géographiques ;
- catégories des cours déjà acquis.

Les opportunités utilisent en plus le matching explicable existant de v85. Pour un recruteur Pro/Business, les talents recommandés sont calculés contre sa dernière offre publiée.

Sans signal personnel, l'endpoint retombe sur une sélection populaire/récente. Aucun profilage publicitaire ni tracking tiers n'est introduit.

## Frontend

- nouvelle route `/search` ;
- barre de recherche globale de la navbar redirigée vers cette route ;
- suggestions après 250 ms à partir de 2 caractères ;
- filtres par type ;
- cartes unifiées responsive ;
- recommandations visibles lorsque la recherche est vide ;
- images en lazy-loading pour limiter la consommation mobile.

## Schéma

v86 n'ajoute aucun modèle et aucune migration de base de données.
