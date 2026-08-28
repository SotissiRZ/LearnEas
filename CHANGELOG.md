# Changelog — Itération sécurité, formation interactive & Afrique

## 🍪 Bug CSRF / connexion admin impossible (correctif critique)

- **Symptôme** : `Interdit (403) — La vérification CSRF a échoué` en essayant de se connecter à
  `/admin/` (ou tout autre formulaire) en déploiement Docker.
- **Cause réelle** : `CSRF_COOKIE_SECURE = True` était forcé dès que `DEBUG=False`, ce qui empêche
  le navigateur d'envoyer le cookie CSRF tant que la connexion n'est pas en HTTPS. Or l'installation
  Docker par défaut sert en HTTP simple (`http://localhost` via nginx, sans certificat TLS) — le
  cookie n'était donc jamais transmis, et **toute requête POST** (login admin, formulaires...)
  échouait systématiquement, quels que soient les identifiants.
- **Correctif** : nouvelle variable d'environnement `USE_HTTPS` (défaut `False`). Les cookies
  "Secure" ne s'activent désormais que si elle est explicitement passée à `True` (cas d'un vrai
  reverse proxy HTTPS devant l'application). `CSRF_TRUSTED_ORIGINS` a aussi un défaut sain
  (`http://localhost,http://127.0.0.1`) même si la variable n'est pas définie.
- **✅ vérifié de bout en bout** : test automatisé simulant un navigateur réel — `GET /admin/login/`
  → cookie CSRF avec `Secure: False` (au lieu de `True` avant le correctif) → `POST /admin/login/`
  avec les vrais identifiants → **`302` (connexion réussie)**, alors que le même scénario donnait
  systématiquement `403` avant.

## 🌐 Bug SSR Docker : catalogue vide sans erreur visible

- **Symptôme** : `/courses`, `/pdfs`, `/formations` et l'accueil affichaient "0 résultat" alors que
  les données existaient bien en base (confirmé via `seed_demo`).
- **Cause réelle** : ces pages effectuent leur appel API **côté serveur** (rendu SSR dans le
  conteneur Next.js), lequel essayait de contacter `http://localhost/api` — or "localhost" à
  l'intérieur de ce conteneur désigne le conteneur lui-même, pas nginx/backend. L'appel échouait
  silencieusement (erreur interceptée pour ne pas casser la page), d'où un "0 résultat" trompeur.
- **Correctif** : nouvelle variable serveur-only `INTERNAL_API_URL` (`http://backend:8000/api`,
  résolue par le DNS interne Docker), utilisée uniquement pour les appels SSR, pendant que
  `NEXT_PUBLIC_API_URL` reste utilisée côté navigateur. **✅ vérifié** par simulation Node.js du
  choix d'URL selon le contexte (serveur vs navigateur).
- Les erreurs API ne sont plus masquées : un bandeau distinct s'affiche désormais si l'API est
  injoignable, différent du message "aucun résultat" (cas normal).

---

Ce document résume les corrections et ajouts apportés suite à la revue complète de la plateforme.
Tout ce qui est marqué **✅ vérifié** a été testé réellement (API réelle, build de production,
migrations sur PostgreSQL) — pas seulement écrit.

## 🔒 Sécurité (critique)

- **Faille corrigée** : cliquer sur "Devenir instructeur" (ou toute URL `/dashboard/*`) sans être
  connecté affichait le contenu du dashboard au lieu de rediriger vers `/login`. Cause : la condition
  de garde ne se déclenchait jamais quand `user` était `null`.
  **✅ vérifié** : inspection du HTML rendu côté serveur confirmant qu'aucune donnée sensible ne fuite
  plus avant authentification.
- Nouveau hook `useAuthGuard()` appliqué systématiquement à toutes les pages `/dashboard/*` et
  `/certificate/*`, avec support de restriction par rôle (`roles: ["admin"]`, etc.) et redirection
  automatique vers `/login?next=...`.
- **Bug de permission corrigé côté API** : un instructeur ne pouvait pas supprimer/modifier ses
  propres vidéos (`Lesson`) car la logique de résolution du propriétaire ne remontait pas la chaîne
  `Lesson → Section → Course → instructor`. **✅ vérifié** : suppression par le propriétaire → `204`,
  suppression par un tiers → `403`.

## 🔑 Authentification

- **Bug d'inscription** : le backend fonctionnait déjà correctement (testé exhaustivement : email
  dupliqué, mots de passe différents, champs manquants → tous correctement rejetés avec message
  clair). Le vrai problème était l'affichage frontend d'un JSON brut illisible en cas d'erreur.
  → Nouveau système de parsing d'erreurs (`ApiError` + `fieldErrors`) affichant un message clair par
  champ, avec validation côté client avant envoi.
- **Mots de passe visibles** : composant `PasswordInput` avec icône œil, utilisé sur login, register
  et réinitialisation de mot de passe.
- **Mot de passe oublié** : flux complet ajouté (backend + frontend) :
  `/api/auth/password-reset/` (demande, ne révèle jamais si un email existe) et
  `/api/auth/password-reset-confirm/` (confirmation avec token à usage unique).
  **✅ vérifié de bout en bout** : demande → email (console en dev) → confirmation → login avec le
  nouveau mot de passe → réutilisation du même token correctement rejetée.
  Pages frontend : `/forgot-password` et `/reset-password/[uid]/[token]`.

## 🎥 Formation interactive (module manquant, réintégré)

Fonctionnalité du cahier des charges d'origine (formations en direct avec instructeur) qui avait été
omise lors de la première refonte. Ajoutée en tant que nouvelle app Django `formations` :

- `InteractiveFormation` : titre, prix, nombre de séances, durée par séance, places max., dates.
- `FormationSession` : séance planifiée avec lien de visioconférence (Jitsi/Zoom/Meet).
- `FormationEnrollment` : inscription après achat.
- **Le lien de réunion n'est visible qu'aux inscrits (et à l'instructeur)** — jamais aux visiteurs
  anonymes ou aux utilisateurs non-inscrits. **✅ vérifié** : `meeting_link: null` avant achat,
  lien réel après achat confirmé.
- Intégré au panier/checkout (`formation_ids` dans le payload de checkout) et au décompte de places
  disponibles (une formation complète ne peut plus être achetée).
- Frontend : catalogue `/formations`, détail `/formations/[slug]`, dashboard instructeur (création +
  planning des séances), dashboard étudiant (`/dashboard/student/formations`, lien "Rejoindre").

## 🎬 Upload et lecture vidéo (vérifiés de bout en bout)

- Le formulaire de gestion de cours accepte désormais **l'upload direct d'un fichier vidéo**
  (en plus du lien externe), avec le même mécanisme que les PDF (`multipart/form-data`).
- **✅ vérifié** : upload réel d'un fichier vidéo via l'API → fichier servi avec
  `Content-Type: video/mp4` et intégralement téléchargeable → lisible par la balise `<video>`.
- **✅ vérifié** : verrouillage correct — une leçon non marquée "aperçu gratuit" renvoie
  `video_file: null` / `video_url: null` tant que l'utilisateur n'est pas inscrit au cours.
- Ajout de la suppression de sections/leçons/PDF directement depuis le dashboard instructeur.
- Le bouton "Publier le cours" est désormais désactivé tant qu'aucune vidéo n'a été ajoutée (évite de
  publier un cours vide).

## 🌍 Orientation Afrique

- **Paiement Mobile Money** ajouté (Orange Money, MTN MoMo, Wave, M-Pesa) en plus de la carte
  bancaire et PayPal, côté modèle (`Order.Provider`) et interface de paiement.
  **✅ vérifié** : achat d'une formation interactive payée en `mobile_money` → commande confirmée →
  accès débloqué.
- Formulaire d'inscription : liste déroulante de pays africains (Maroc, Sénégal, Côte d'Ivoire,
  Cameroun, Mali, Nigeria, Kenya, Égypte, etc.) au lieu d'un champ texte libre.
- Page d'accueil et métadonnées repositionnées : "La plateforme de formation en ligne pensée pour
  l'Afrique".

## 🗄️ Base de données

- **PostgreSQL installé et testé réellement** dans l'environnement de développement (pas seulement
  configuré en théorie) : migrations complètes exécutées avec succès, y compris les nouvelles tables
  `formations`. Le projet reste compatible SQLite en développement rapide si besoin
  (`DATABASE_URL` non défini).

## 🧑‍🤝‍🧑 Données de démonstration enrichies

La commande `seed_demo` a été entièrement réécrite pour couvrir toutes les fonctionnalités :

| Élément | Avant | Maintenant |
|---|---|---|
| Instructeurs | 1 | 3 (Dév. web, Data & IA, Design), domaines et pays différents |
| Étudiants de test | 0 | 3 (Sénégal, Cameroun, Mali) |
| Cours | 1 | 8, répartis sur 6 catégories |
| PDF vendus seuls | 1 | 4 |
| Formations interactives | 0 | 3, avec séances planifiées et liens de réunion |
| Avis | 0 | 4, avec recalcul automatique de la note moyenne |
| FAQ | 0 | 5 questions/réponses |

**✅ vérifié** : `python manage.py seed_demo` exécuté sur base PostgreSQL fraîche, toutes les
données confirmées accessibles via l'API (8 cours, 4 PDF, 3 formations, 6 catégories, 5 FAQ).

## Comptes de démonstration

| Rôle | Email | Mot de passe |
|---|---|---|
| Admin | admin@learneas.com | admin1234 |
| Instructeur (Dév. web) | sarah@learneas.com | instructor1234 |
| Instructeur (Data & IA) | koffi@learneas.com | instructor1234 |
| Instructeur (Design) | amina@learneas.com | instructor1234 |
| Étudiant | fatou@learneas.com | student1234 |
| Étudiant | jean@learneas.com | student1234 |
| Étudiant | aicha@learneas.com | student1234 |

## Ce qui reste à faire (transparence)

- Intégration réelle d'un agrégateur Mobile Money (CinetPay, Flutterwave, PawaPay...) — actuellement
  la confirmation de paiement est simulée comme pour Stripe/PayPal, prête à être branchée sur un vrai
  webhook.
- Envoi d'email réel en production (le lien de réinitialisation de mot de passe s'affiche dans les
  logs backend en développement ; configurer `EMAIL_HOST`/`EMAIL_HOST_USER` en prod).
- Interface de gestion des utilisateurs pour l'admin (actuellement via `/admin` Django uniquement).

## 2026-08-28 — Back-office administrateur v4

- Ajout d'une sidebar d'administration persistante : Aperçu, Utilisateurs, Contenus, Commandes,
  Versements, Séances live, Catégories, FAQ/Avis et Paramètres.
- Tous les KPI de l'aperçu sont cliquables et conduisent vers la vue détaillée correspondante.
- Correction de la navigation `?tab=...` : les anciens boutons Aperçu/Utilisateurs/Commandes
  modifiaient l'URL sans changer réellement le contenu affiché.
- Cartes « Versements instructeurs » et « Contrôle des séances » limitées à 310 px avec zone
  interne scrollable pour conserver un dashboard compact.
- Le rapport « Participants & durées » s'ouvre désormais dans une modale avec état de chargement,
  gestion des erreurs, organisateurs, heures d'entrée/sortie et temps de présence agrégé.
- Gestion utilisateurs côté back-office : création de comptes, recherche, filtre rôle/état, changement
  de rôle et activation/désactivation, avec protection empêchant la suppression du dernier administrateur actif.
- Gestion éditoriale : publication/dépublication/suppression des cours, PDF et formations, mise en avant
  des cours/PDF réservée à l'administrateur, gestion des catégories et de la FAQ.
- Modération des avis avec recalcul de la note moyenne après suppression.
- Gestion des commandes : recherche/filtres, détail d'une facture, réconciliation du statut payé
  et réparation des droits d'accès.
- Gestion des versements : filtres, destination de paiement, validation ou échec avec référence/note.
- Ajout de `PlatformSettings` : inscriptions, demandes instructeur, commission et retrait minimum
  sont configurables depuis l'interface admin et appliqués côté backend.
- Les comptes de test restent documentés dans le README comme règle de livraison du projet.
### Administration v4 — compléments
- Ajout d’un workflow réel de **demande instructeur** : dépôt étudiant, statut en attente, approbation/refus par un admin et motif de refus.
- Nouveau menu **Demandes instructeur** dans la sidebar admin avec recherche, filtre, détail et actions.
- Le dépôt d’une demande ne promeut plus automatiquement un étudiant au rôle instructeur.
- Ajout de raccourcis de création de contenu depuis le back-office admin.
- Les filtres issus des URL/KPI sont réinitialisés correctement lorsqu’on change de lien dans un même onglet admin.



## 2026-08-28 — Back-office instructeur v5

- Ajout d’une **sidebar instructeur** persistante et responsive : Aperçu, Mes cours, Mes PDF,
  Formations live, Séances live, Étudiants, Statistiques, Avis & questions, Revenus & versements,
  Messages et Profil & paramètres.
- Refonte de l’aperçu avec KPI cliquables et données strictement limitées aux contenus de
  l’instructeur : contenus publiés, étudiants uniques, note moyenne, questions, ventes et solde.
- Ajout d’une vue **Étudiants** avec recherche, filtre par type d’accès (cours/formation/PDF),
  progression et raccourci vers la messagerie.
- Ajout d’une vue **Statistiques** avec chiffre d’affaires, gains instructeur, évolution mensuelle et
  classement des contenus par ventes/revenus.
- Ajout d’un espace **Revenus & versements** : ventes récentes, export CSV, profil de paiement,
  solde disponible, demande de retrait et historique des versements.
- Ajout d’une vue **Avis & questions** avec consultation des notes et réponse aux questions liées aux
  leçons de l’instructeur.
- Ajout d’une vue **Séances live** avec filtres, accès à la salle LearnEas et rapports de présence
  (heures d’entrée/sortie et durée).
- Ajout de la **messagerie instructeur** dans le shell du dashboard et possibilité de démarrer une
  conversation depuis la liste des étudiants.
- Ajout de **Profil & paramètres** : photo, identité publique, bio, expertise, expérience et changement
  de mot de passe. L’email reste l’identifiant de connexion ; le username demeure technique.
- Gestion enrichie des cours, PDF et formations : recherche, filtres, édition des métadonnées et
  couvertures, publication/dépublication, suppression et accès direct à la gestion du contenu/planning.
- Nouveaux endpoints instructeur agrégés pour l’aperçu, les étudiants, les séances, les avis/questions
  et les statistiques financières, avec contrôle de rôle et scoping côté serveur.
- Ajout de tests de régression pour l’isolation des données instructeur, le changement de mot de passe
  et le filtrage des séances.
- Les comptes de test restent documentés dans le README.

## 2026-08-28 — Correctif build frontend v6

- Correction du typage TypeScript de `InstructorSidebar.tsx` qui bloquait `next build` avec
  `Property 'exact' does not exist...`.
- La configuration des éléments de navigation utilise maintenant un type explicite
  `InstructorNavItem` avec `exact?: boolean`, et la valeur est normalisée à `false` lors du rendu.
- Aucun changement fonctionnel ou visuel de la sidebar : ce correctif vise uniquement la compilation
  de production et conserve la navigation introduite en v5.
