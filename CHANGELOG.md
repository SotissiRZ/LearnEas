# v27 — Correction du démarrage backend

- Correction du `SystemCheckError models.E034` sur `FormationSessionInvite`.
- Nom de l’index `(session, email)` raccourci de `formation_invite_session_email_idx` à `form_inv_sess_email_idx` pour respecter la limite Django de 30 caractères.
- Modèle et migration `0007_session_email_invites.py` alignés pour éviter toute divergence de schéma.

---

# v26 — Correctif build Navbar / Administration technique

- Correction de l’erreur JSX bloquante dans `components/layout/Navbar.tsx` introduite par le lien **Administration technique** du menu mobile.
- La branche utilisateur connectée du menu mobile est désormais correctement enveloppée dans un fragment React.
- Le lien **Administration technique** reste réservé aux administrateurs et ferme le menu mobile lors de son ouverture.
- Validation syntaxique de l’ensemble des fichiers TypeScript/TSX du frontend.

---

# v25 — Indicateurs live intégrés au titre & administration technique

- Les indicateurs **Participants, Mains, Live et Planifié** sont désormais de petites pastilles affichées directement à la suite du titre de la réunion.
- Le titre de séance possède une largeur maximale responsive et est tronqué proprement pour éviter tout débordement.
- Suppression de l’ancienne rangée dédiée aux indicateurs afin de libérer davantage d’espace vertical pour la scène, l’éditeur et le tableau blanc.
- Le bouton **Indicateurs** continue de masquer/réafficher ces mini-indicateurs.
- Ajout dans le menu de profil des administrateurs d’un bouton **Administration technique** ouvrant Django Admin dans un nouvel onglet.
- Le même accès est disponible dans le menu mobile pour les comptes administrateurs.

---

# v24 — Réunion enrichie : profil, éditeur flexible, durée fiable et tableau blanc

- Refonte de la tuile vidéo locale : profil organisateur compact avec avatar/initiale et nom en surimpression ; lorsque la caméra est coupée, l’avatar remplace proprement le flux noir.
- Correction du bouton caméra : réactivation du track existant ou réacquisition de la caméra si le track a été interrompu, synchronisation du flux local et des pairs WebRTC.
- Barre de contrôles du bas réductible/déployable ; en mode compact seuls les icônes restent visibles afin de libérer la scène principale.
- Ajout du **tableau blanc collaboratif** avec dessin tactile/souris, couleurs, épaisseur, annulation et effacement synchronisés entre participants.
- Éditeur de code amélioré avec thèmes Midnight/Dracula/Clair, coloration syntaxique légère et console redimensionnable par glisser-déposer ou boutons +/- .
- Rapport de séance corrigé : la présence est recalculée dans la fenêtre réelle de la séance et n’utilise plus directement les anciennes durées potentiellement gonflées. Les durées sont affichées en heures/minutes/secondes réelles.
- Le rapport instructeur présente désormais l’organisateur de façon plus compacte avec avatar, nom et email.
- Ajout du signal collaboratif `whiteboard` et de la migration `0008_whiteboard_signal.py`.
- Tests de régression ajoutés pour le tableau blanc et les anciennes présences anormalement longues.

---

# v23 — Invitations email aux séances live

- L'organisateur peut inviter un apprenant **non inscrit à la formation** avec son adresse email.
- L'invitation donne accès uniquement à la séance concernée et ne crée aucune inscription à la formation.
- Une adresse correspondant déjà à un compte LearnEas obtient immédiatement l'accès invité ; une adresse sans compte reste en attente jusqu'à l'inscription avec le même email.
- Email d'invitation avec lien direct vers la salle et lien d'inscription prérempli.
- Les invités apparaissent avec le rôle **Invité** dans les présences live.
- États d'invitation visibles par l'organisateur : compte trouvé, compte à créer, séance rejointe, invitation révoquée.
- L'organisateur peut révoquer une invitation.
- Les invités ne sont pas ajoutés aux inscrits et ne deviennent pas éligibles au certificat de formation par cette invitation.
- Migration Django : `0007_session_email_invites.py`.

---

# v22 — Sidebar rail sans chevauchement

- Correction du rail latéral Admin et Instructeur qui recouvrait le contenu au survol.
- Sur grand écran, le contenu principal passe de 64 px à 240 px de marge gauche en même temps que la sidebar s’ouvre.
- Transition synchronisée entre sidebar et contenu pour éviter tout masquage de titre, filtre, tableau ou bouton.
- Le rail reste collé au bord gauche et se replie en icônes lorsque le pointeur le quitte.

---

# v21 — Sidebars desktop en rail d’icônes expansible

- Les sidebars **Administration** et **Instructeur** sont maintenant collées au bord gauche de l’écran sur grand écran.
- Largeur réduite à **64 px** au repos avec uniquement les icônes visibles.
- Au survol, le rail s’élargit à **240 px** et révèle les libellés avec une transition douce.
- L’ouverture se fait en superposition afin d’éviter tout décalage du contenu central.
- Le contenu principal réserve uniquement la largeur du rail réduit et conserve son scroll indépendant.
- Sur mobile et tablette, la navigation horizontale sticky existante est conservée.

---

# v20 — Navbar et sidebars dashboard figés

- Dashboards **Admin** et **Instructeur** verrouillés dans la hauteur disponible sous la navbar sur desktop.
- La navbar reste visible pendant toute la navigation du dashboard.
- Les sidebars Admin/Instructeur ne défilent plus avec le contenu principal.
- Le contenu central possède désormais son propre scroll vertical.
- Si le menu latéral dépasse la hauteur de l’écran, seul le menu lui-même défile.
- Sur mobile/tablette, le menu dashboard reste sticky sous la navbar et conserve sa navigation horizontale.
- Le footer ne vient plus interrompre le travail dans les dashboards sur desktop.

---

# v19 — Salle live épurée, panneaux repliables & exécution Python

- **Espace de travail prioritaire** : en-tête réduit à une seule ligne et indicateurs transformés en mini-cartes très compactes.
- Boutons **Indicateurs**, **Panneau** et **Focus** pour masquer/réafficher les zones secondaires à la demande.
- Panneau Participants / Chat / Fichiers repliable afin d’agrandir instantanément la scène ou l’éditeur.
- Console de l’éditeur de code repliable afin de donner toute la largeur au code.
- Barre de contrôles inférieure élargie et forcée sur **une seule ligne** sur les grands écrans.
- Boutons d’action rendus plus explicites, avec messages d’erreur pour Démarrer/Terminer et fallback de copie.
- **Python exécutable dans le navigateur** via Pyodide/WebAssembly (version épinglée), avec capture de stdout/stderr.
- JavaScript reste exécuté dans une iframe sandboxée ; HTML et CSS disposent d’un aperçu direct.
- Java, C, C++ et texte restent éditables/partageables mais le bouton Exécuter est désactivé avec une explication au lieu de sembler cassé.
- CSP nginx adaptée pour autoriser la version épinglée de Pyodide depuis jsDelivr et WebAssembly.
- **JWT** : ajout du renouvellement automatique du jeton d’accès sur réponse 401 puis répétition de la requête, afin d’éviter les boutons/API inactifs après expiration du token.

---

# v18 — Salle live encore plus compacte

- Réduction supplémentaire de la taille des éléments de la salle live : en-tête, KPI, carte d'entrée, scène vidéo, panneau latéral et barre d'actions.
- Tuiles vidéo et états vides moins hauts pour limiter l'effet de zoom.
- Éditeur de code compacté : barre d'outils, sélecteurs, panneau console et zone d'édition allégés.
- Largeur utile augmentée pour mieux exploiter l'écran tout en diminuant l'encombrement visuel.

---

# v17 — Salle live fixe & éditeur de code intégré

- La salle live occupe désormais **100 % du viewport** en couche fixe : le header et le footer du site ne peuvent plus apparaître pendant la réunion.
- La barre supérieure, les KPI de séance et la barre de contrôles restent fixes ; seuls les panneaux internes (participants, chat, fichiers, scène) peuvent défiler si nécessaire.
- Ajout d’un **éditeur de code intégré et partagé** avec :
  - JavaScript, HTML, CSS, Python, Java, C, C++ et texte ;
  - numéros de ligne et gestion de la touche Tab ;
  - nom de fichier, copie et téléchargement ;
  - exécution JavaScript dans une iframe sandboxée ;
  - aperçu HTML sandboxé ;
  - synchronisation en direct du code avec les participants présents.
- Ajout du signal live `code` côté backend et migration `0006_shared_code_signal`.

---

# v16 — Salle live allégée visuellement

- Réduction de l’effet de zoom sur la salle de visioconférence.
- Éléments globalement allégés : titres, cartes KPI, panneaux latéraux, boutons d’action et barre flottante.
- Scène vidéo plus compacte avec tuiles et zones vides moins hautes.
- Largeur maximale de page augmentée pour mieux exploiter les grands écrans.
- Panneau de périphériques et messagerie resserrés pour améliorer la densité d’information.

---

# v15 — Cartes instructeurs allégées & suppression des tirets longs

- Réduction de la taille des cartes de la page **Nos instructeurs** : hauteur minimale abaissée, avatar plus petit, textes réduits et bouton plus compact.
- Description instructeur limitée à 2 lignes pour éviter les cartes trop hautes.
- Suppression des tirets longs **`—`** dans l’interface frontend, remplacés par des séparateurs plus légers ou retirés selon le contexte.
- Cohérence visuelle améliorée sur les cartes, les listes, les pages catalogue et plusieurs libellés UI.

---

# v14 — Correctif build TypeScript de la salle live

- Correction du build Next.js bloqué sur `room is possibly null` dans la boucle de présence de la visioconférence.
- La référence de salle est désormais capturée dans une constante non nullable après le garde `if (!attendanceId || !room) return`, ce qui conserve la sûreté de type dans la fonction asynchrone interne.
- Aucun assouplissement TypeScript (`!`, `any`, désactivation de `strict`) n'a été ajouté : le correctif conserve les contrôles de type.

---

# v13 — Visioconférence collaborative avancée

- Ajout de la **levée de main** persistée dans la présence de séance et visible en temps réel.
- Ajout du **choix du microphone et de la caméra** sans quitter la salle.
- Ajout du **mode plein écran** sur la scène vidéo.
- Ajout d'une **modération organisateur** : couper le micro, couper la caméra ou retirer un participant.
- Ajout du **partage de fichiers** dans la salle live avec limite de 20 Mo, blocage des extensions exécutables et téléchargement authentifié.
- Ajout d'un **enregistrement local organisateur** de la grille vidéo et du mix audio disponibles dans le navigateur, exporté en WebM à l'arrêt.
- Le panneau latéral live comporte désormais trois onglets : **Participants, Chat, Fichiers**.
- Migration `0005_live_room_collaboration` : état de main levée, signal de modération et fichiers de séance.
- Ajout de tests de régression backend pour la main levée, les permissions de modération et le partage/téléchargement de fichiers.

---

# v12 — Refonte des cartes instructeurs & enrichissement de la visioconférence

- Refonte de la page **Nos instructeurs** : cartes plus structurées, meilleure hiérarchie visuelle, bouton **Contacter** déplacé en **bas à droite** avec un fond vert de marque.
- Le composant `ContactInstructorButton` accepte désormais un libellé et des classes personnalisées, ce qui permet d’uniformiser son rendu selon le contexte.
- La salle **visioconférence** a été enrichie :
  - partage d’écran via `getDisplayMedia`,
  - panneau latéral **Participants / Chat**,
  - messagerie de séance en temps réel,
  - indicateurs de durée, présence et outils disponibles,
  - barre de contrôles plus complète (micro, caméra, partage d’écran, chat, quitter).
- Backend live sessions : le modèle de signalisation accepte maintenant aussi les messages de type `chat` en plus des signaux WebRTC.

---

# v11 — Agrandissement des KPI du dashboard administrateur

- Les 8 KPI du tableau de bord administrateur sont désormais affichés sur **4 colonnes maximum** sur grand écran, soit 2 lignes lorsque les 8 cartes sont visibles.
- Cartes KPI agrandies : hauteur minimale, padding et icônes augmentés pour une meilleure lisibilité.
- Suppression du `truncate` sur les valeurs financières et numériques afin qu'elles ne soient plus affichées sous forme `9...`, `1...`, etc.
- Les valeurs et libellés peuvent revenir proprement à la ligne sans déborder de la carte.
- Responsive conservé : 1 colonne mobile, 2 petites tablettes, 3 écrans intermédiaires, 4 grands écrans.

---

# v10 — Correctif démarrage Docker local / SECRET_KEY

- Correction du crash `RuntimeError: SECRET_KEY invalide pour la production` lors d’un lancement local avec `docker compose up`.
- `docker-compose.yml` utilise désormais `DEBUG=True` et `dev-secret-key-change-me` **uniquement comme valeurs par défaut locales**.
- `.env.docker.example` et `backend/.env.example` sont alignés sur le mode développement local.
- Les garde-fous de production Django restent inchangés : avec `DEBUG=False`, une clé faible/de développement et `ALLOWED_HOSTS=*` sont toujours refusés.
- La production Railway reste explicitement configurée via variables d’environnement, sans secret de production dans le dépôt.

---

# v9 — Audit sécurité, performance et mobile-first

- Migration frontend vers **Next.js 15.5.21** et adaptation des pages serveur aux `params/searchParams` asynchrones.
- Django **5.2.17 LTS**, DRF 3.18.0 et SimpleJWT 5.5.1.
- Checkout Stripe réel avec webhook signé ; confirmation manuelle d’une commande payante bloquée en production.
- Réservations temporaires atomiques des places de formations live pour éviter la survente pendant un checkout externe.
- Médias pédagogiques privés derrière URLs signées et `X-Accel-Redirect` nginx ; couvertures restent publiques.
- Throttling DRF centralisé dans Redis, JWT raccourci/rotatif avec blacklist et garde-fous de configuration production.
- Backend/Celery exécutés sans privilèges root après le bootstrap de volumes.
- Index PostgreSQL ajoutés aux chemins de requête catalogue, formations et commandes.
- Inscription simplifiée : l’email est l’identifiant utilisateur ; le username technique est généré automatiquement.
- Durcissement permissions sur messagerie, avis/questions, wishlist, séances live et transitions financières.
- Responsive mobile-first renforcé (320–412 px), tiroir curriculum mobile, cibles tactiles, formulaires mono-colonne et lecteurs adaptés.
- Messages marketing de paiement alignés sur les moyens réellement activés.
- CI automatisée : checks/migrations/tests Django, `npm build`, audit mobile et validation Compose.
- Ajout de `AUDIT.md` avec risques résiduels et checklist de production.

---

## v8 — Correctif CSRF inscription / API JWT

- L’API REST utilise désormais uniquement `JWTAuthentication`.
- Correction du `CSRF Failed: CSRF token missing` pouvant survenir à l’inscription ou à la connexion lorsqu’un cookie de session Django Admin était déjà présent dans le navigateur.
- La protection CSRF du Django Admin reste inchangée et active.
- Ajout d’un test de régression avec une session admin existante et les contrôles CSRF activés.

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

---

# v7 — Légal, lecteurs enrichis et certificats

## ⚖️ Footer et conformité

- Ajout d'une section **Légal** dans le footer : Conditions d'utilisation, Confidentialité, Mentions légales, Cookies, Paiements & remboursements et Vérification de certificat.
- Les informations juridiques de la plateforme sont administrables depuis le back-office : raison sociale, adresse, pays, immatriculation, identifiant fiscal, email confidentialité et délai de remboursement.
- Les pages légales utilisent les paramètres publics de la plateforme afin d'éviter des informations divergentes entre le footer et l'administration.

## 🎬 Lecteurs intégrés

- Nouveau lecteur vidéo commun aux écrans apprenant et instructeur : contrôles natifs, lecture/pause, saut ±10 s, volume/muet, vitesse 0,5×–2×, boucle, redémarrage, plein écran, Picture-in-Picture, sous-titres WebVTT, raccourcis navigateur, nouvel onglet et téléchargement.
- Les leçons peuvent désormais contenir un fichier **WebVTT** et une **transcription** ; l'apprenant dispose d'un onglet Transcription dans le lecteur du cours.
- Nouveau lecteur PDF unifié avec barre native du navigateur, navigation par pages, recherche, zoom, miniatures lorsque le navigateur les supporte, plein écran, impression, nouvel onglet et téléchargement.

## 🏆 Certificats

- Nouvel onglet apprenant **Mes certificats** avec recherche, filtres, statut, consultation, impression/enregistrement PDF, partage et vérification publique.
- Certificat de cours configurable : activation, délivrance automatique, seuil de progression, validité, titre, sous-titre, description, signataire, couleur, préfixe et informations visibles.
- Certificat de formation interactive configurable selon le **taux de présence réel** enregistré dans les séances LearnEas.
- Espace instructeur **Certificats** : configuration par contenu, candidats éligibles, délivrance individuelle, registre, révocation et réémission.
- Espace admin **Certificats** : paramètres globaux, surcharge par contenu, registre global, délivrance forcée exceptionnelle, révocation/réémission et activation de la vérification publique.
- Chaque certificat conserve un snapshot des informations au moment de l'émission et dispose d'un numéro ainsi que d'un code de vérification uniques.
- La vérification publique ne révèle pas l'adresse email de l'apprenant.
- `seed_demo` génère un certificat de démonstration pour **Fatou Ndiaye** afin de tester immédiatement le parcours apprenant.
