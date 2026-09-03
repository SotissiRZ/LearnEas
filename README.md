# LearnEas

> **v41 — Visioconférence :** pendant un partage d’écran, la caméra du présentateur est affichée en vignette déplaçable et intégrée au flux présenté.


> **Mise à jour majeure** — voir [`CHANGELOG.md`](./CHANGELOG.md) pour le détail des corrections de
> sécurité, du module Formation Interactive, de l'orientation Afrique (Mobile Money, pays africains)
> et de toutes les vérifications effectuées.

Plateforme de formation en ligne — refonte du projet PFE "Gestion de la formation en ligne" (Laravel)
en **Django REST Framework + Next.js**, avec un nouveau paradigme :

> On n'achète plus une vidéo isolée. On achète un **cours complet** (playlist entière avec toutes ses
> vidéos organisées en modules) ou un **PDF** — vendu seul ou inclus dans un cours.

Style visuel de plateforme de formation premium avec une identité propre (palette verte, cartes arrondies,
dashboards dédiés par rôle et espace de lecture immersif).

---

## 🏗️ Architecture

```
learneas/
├── docker-compose.yml       Orchestration Docker locale complète (db, redis, backend, celery, frontend, nginx)
├── docker-compose.dev.yml   Orchestration développement (hot-reload)
├── .env.docker.example      Variables d'environnement Docker
├── Makefile                 Raccourcis (make up, make logs, make migrate...)
├── docker/nginx/            Configuration du reverse proxy
├── backend/     Django 5 + Django REST Framework (API JSON, JWT, admin) — Dockerfile inclus
└── frontend/    Next.js 15.5 (App Router) + TypeScript + Tailwind CSS — Dockerfile inclus
```

Les deux projets communiquent exclusivement via l'API REST (`/api/...`). Le frontend n'accède jamais
directement à la base de données. En Docker, `nginx` est l'unique point d'entrée public : il route
`/api` et `/admin` vers le backend, `/static` et `/media` vers les volumes partagés, et tout le reste
vers le frontend Next.js.

---

## 👤 Comptes de test / démonstration

> Ces comptes sont destinés uniquement au développement et aux démonstrations. Ne pas utiliser ces
> mots de passe en production.

Les utilisateurs de test sont créés par la commande Django `seed_demo`.

| Rôle | Nom | Username | Email | Mot de passe |
|---|---|---|---|---|
| Administrateur | Admin LearnEas | `admin` | `admin@learneas.com` | `admin1234` |
| Instructeur | Sarah Benali | `sarah_dev` | `sarah@learneas.com` | `instructor1234` |
| Instructeur | Koffi Adjei | `koffi_data` | `koffi@learneas.com` | `instructor1234` |
| Instructeur | Amina Diop | `amina_design` | `amina@learneas.com` | `instructor1234` |
| Étudiant | Fatou Ndiaye | `student_fatou` | `fatou@learneas.com` | `student1234` |
| Étudiant | Jean Mbeki | `student_jean` | `jean@learneas.com` | `student1234` |
| Étudiant | Aïcha Traoré | `student_aicha` | `aicha@learneas.com` | `student1234` |

### Créer / recréer les données de démonstration

Avec Docker :

```bash
docker compose exec backend python manage.py seed_demo
```

Sans Docker, depuis `backend/` :

```bash
python manage.py seed_demo
```

En développement avec `docker-compose.dev.yml`, `SEED_DEMO=true` est déjà activé et les comptes sont
créés automatiquement au démarrage. Avec `docker-compose.yml`, la valeur par défaut est
`SEED_DEMO=false` : utilisez la commande ci-dessus ou définissez `SEED_DEMO=true` dans `.env`.

Connexion frontend : **http://localhost/login**  
Admin Django : **http://localhost/admin**

---

## ✅ Fonctionnalités implémentées

### Légal, lecteurs et certificats (v7)

- Footer enrichi avec une section **Légal** : conditions d'utilisation, confidentialité, mentions légales, cookies, paiements/remboursements et vérification publique des certificats.
- Les informations juridiques (raison sociale, adresse, pays, immatriculation, identifiant fiscal, email confidentialité et délai de remboursement) sont configurables dans **Admin → Paramètres**.
- Lecteur vidéo unifié : contrôles personnalisés, ±10 s, volume/mute, vitesse 0,5× à 2×, sous-titres WebVTT, Picture-in-Picture, plein écran et raccourcis clavier (K/Espace, J/L, flèches, M, F, C). Les vidéos de cours ne proposent ni téléchargement ni ouverture directe de la source.
- Streaming adaptatif HLS : 240p/360p/480p/720p selon la résolution source, qualité Auto, mode **Économie de données ≤360p** et mode **Audio uniquement ~48 kb/s**. Les préférences faible débit sont adaptées aux connexions mobiles et le lecteur peut activer automatiquement l'économie de données sur 2G/`Save-Data`.
- Lecteur PDF unifié : barre native du navigateur (pages, recherche, zoom, miniatures selon navigateur), plein écran/modal, impression, nouvel onglet et téléchargement.
- Upload vidéo instructeur : MP4/WebM/MOV/M4V, progression réelle, métadonnées extraites automatiquement et limite Docker locale de 2 Go par défaut (`MAX_VIDEO_UPLOAD_MB`).
- Les leçons acceptent désormais un fichier de sous-titres `.vtt` et une transcription.
- **Apprenant → Mes certificats** : registre personnel, filtres, affichage, impression/PDF, partage et vérification publique.
- **Instructeur → Certificats** : règles par cours/formation, seuil de progression ou de présence réelle, délivrance automatique/manuelle ou groupée, validité, apparence, signataire, préfixe, registre, révocation et réémission.
- **Admin → Certificats** : registre global, vérification/révocation/réémission, délivrance groupée ou forcée et paramètres globaux + surcharge par contenu.
- La présence aux formations live est calculée à partir du temps réellement enregistré dans les séances, et non d'une simple case « présent ».
- `seed_demo` délivre un certificat d'exemple à **Fatou Ndiaye** sur le cours Django pour tester immédiatement l'onglet « Mes certificats ».


### Expérience de lecture des cours (v37)

- Sommaire de cours repliable avec chapitres, durée, progression et leçon active.
- Navigation précédent/suivant et lecture automatique de la leçon suivante.
- Reprise automatique à la dernière leçon et au dernier timestamp enregistré.
- Onglets **Aperçu**, **Transcription**, **Carnet**, **Q&R** et **Ressources** sous le lecteur.
- Transcriptions recherchables ; utilisez le format `[01:25] Texte du passage` pour rendre un passage cliquable.
- Carnet privé avec notes horodatées, édition/suppression, retour instantané au passage et export texte.
- Q&R directement relié aux commentaires de la leçon et aux réponses de l'instructeur.
- Migration à appliquer après mise à jour : `python manage.py migrate`.

### Cohortes & mentorat 1:1 (v45)

- Les formations synchrones sont structurées en **cohortes** : nom de promotion, places min/max, clôture des inscriptions, fuseau horaire et planning exportable en `.ics`.
- Les instructeurs peuvent publier des **offres de mentorat individuel**, ouvrir des créneaux, fixer durée/prix/délais et recevoir des réservations dans une salle vidéo LearnEas privée.
- Les séances payantes passent par le checkout existant et alimentent automatiquement les revenus/commissions instructeur ; Mobile Money et devises locales restent compatibles.
- L'apprenant dispose de **Mes rendez-vous de mentorat** et le mentor d'un espace de gestion dédié.
- Les rappels WhatsApp peuvent prévenir les deux parties avant le rendez-vous.
- Les champs **Pays** utilisent un référentiel sélectionnable (marchés africains francophones en tête) au lieu d'une saisie libre ; WhatsApp et Mobile Money utilisent un sélecteur **pays + indicatif** puis le numéro national.
- Les numéros sont enregistrés au format international E.164 et revalidés côté API ; les pays sont eux aussi normalisés côté serveur.
- Le cycle réservation/paiement empêche la libération d'un créneau pendant une transaction externe encore en attente et conserve l'historique des offres/créneaux déjà réservés.
- Voir `docs/MENTORSHIP.md` pour le flux, l'API et les règles de réservation.

### Catalogue
- Cours = **playlist complète** : sections → leçons vidéo, durée totale et nombre de vidéos calculés
  automatiquement (signal Django).
- PDF **inclus dans un cours** (ressource additionnelle) ET PDF **vendus seuls** (catalogue indépendant).
- Catégories avec icônes (lucide-react), niveaux (débutant/intermédiaire/expert), langue, prix, promo.
- Recherche, filtres (catégorie, niveau, gratuit), tri (récent, prix, note, popularité).

### Achat & accès
- Panier persisté localement et checkout à passerelles configurables côté administrateur.
- Drivers intégrés : **Stripe**, **YouCan Pay**, **GeniusPay**, **CinetPay Mobile Money** et **paiement manuel**. Les secrets restent exclusivement dans les variables d’environnement serveur.
- L’administrateur active/désactive les moyens de paiement, choisit leurs devises et leur mode test, et peut exécuter un diagnostic de connexion sans débiter un client.
- Les devises (code ISO, symbole, taux, précision, devise de checkout par défaut) sont administrables sans redéploiement. **EUR est la devise comptable de base** des prix et revenus ; son taux vaut toujours 1.
- Un **sélecteur de devise dans la navbar** permet à chaque visiteur de choisir sa devise d'affichage. Les prix sont convertis depuis l'EUR avec le taux actif configuré par l'administrateur, la préférence est mémorisée et le checkout reprend automatiquement cette devise.
- Chaque commande mémorise l’environnement `sandbox/live` utilisé afin qu’un changement ultérieur de configuration ne fasse pas vérifier une transaction avec les mauvaises clés.
- Une commande peut contenir plusieurs cours, PDF et formations live en même temps.
- **Le contenu vidéo/PDF est verrouillé côté API tant que l'achat n'est pas confirmé** (pas juste côté
  affichage) — vérifié par tests réels (voir plus bas).
- Leçons en "aperçu gratuit" consultables sans achat.

### Mobile Money Afrique francophone (v42)

LearnEas intègre désormais CinetPay comme premier connecteur Mobile Money de production. La comptabilité interne reste en EUR, tandis que XOF/XAF servent à l’affichage et au paiement local.

Variables serveur :

```env
# URL publique du backend (Railway en production). CinetPay doit pouvoir joindre /api/payments/cinetpay/webhook/
BACKEND_PUBLIC_URL=https://api.votre-domaine.com

# Production
CINETPAY_API_KEY=
CINETPAY_SITE_ID=
CINETPAY_SECRET_KEY=

# Sandbox / identifiants de test
CINETPAY_SANDBOX_API_KEY=
CINETPAY_SANDBOX_SITE_ID=
CINETPAY_SANDBOX_SECRET_KEY=
```

Après avoir renseigné les clés : **Administration → Paramètres → Paiements & devises → CinetPay Mobile Money**, activez la passerelle. Le checkout utilise le canal Mobile Money et CinetPay affiche les opérateurs disponibles selon le pays et la devise. Le preset v42 démarre en **live désactivé** avec XOF uniquement : la documentation CinetPay indique actuellement que ses sandboxes sont temporairement indisponibles, et un compte marchand CinetPay ne peut encaisser que dans la devise autorisée pour ce compte. Pour un service XAF distinct, configurez un compte/service marchand compatible avant d'ajouter XAF aux devises de la passerelle.

En local, le guichet CinetPay peut être initialisé, mais le webhook ne pourra pas atteindre `localhost`. Pour tester le cycle complet, utilisez un tunnel HTTPS public vers Nginx/Django ou déployez temporairement le backend sur Railway puis définissez `BACKEND_PUBLIC_URL`.

La délivrance du contenu ne dépend jamais du simple retour navigateur : LearnEas vérifie le webhook HMAC et relit le statut directement auprès de CinetPay avant de marquer la commande comme payée.

### Apprentissage
- Espace d'apprentissage dédié (`/learn/[slug]`) : lecteur vidéo, sidebar curriculum, suivi de
  progression leçon par leçon, onglet ressources PDF, onglet discussion (base posée).
- Barre de progression par cours, calcul automatique du `%` de complétion.
- **Certificat configurable** : délivrance automatique à partir du seuil défini sur le cours, ou du taux de présence réel pour une formation live ; page imprimable/enregistrable en PDF et vérification publique par code.

### Salle live / visioconférence
- Salle WebRTC interne avec caméra et microphone, présence réelle et suivi du temps de connexion.
- Lorsqu’un participant coupe sa caméra, LearnEas **arrête réellement la piste vidéo** (`MediaStreamTrack.stop()`), libère le périphérique et détache la piste WebRTC. Le prochain allumage recrée une nouvelle capture ; la modération organisateur applique la même règle.
- Partage d'écran natif navigateur, chat de séance, levée de main et panneau des participants.
- Choix du microphone et de la caméra pendant la séance, ainsi que mode plein écran.
- Pour l'organisateur : commandes de modération (couper micro/caméra, retirer un participant).
- Partage de fichiers de séance avec téléchargement authentifié et limite de 20 Mo par fichier.
- Invitation ponctuelle par email d'un apprenant non inscrit : accès limité à la séance, statut d'invitation et révocation par l'organisateur, sans création d'une inscription à la formation.
- Enregistrement local côté organisateur de la grille vidéo et du mix audio disponibles au moment de l'enregistrement ; le fichier WebM est téléchargé sur le poste de l'organisateur et n'est pas stocké automatiquement sur le serveur.
- **Mini-IDE collaboratif multi-fichiers** : création/renommage/suppression de fichiers, projets libres/POO et modèles React, Next.js, Django, Django REST Framework, FastAPI, Flask et Node/Express.
- Coloration syntaxique et thèmes d’éditeur ; console redimensionnable. JavaScript/HTML/CSS s’exécutent dans des iframes sandboxées et Python dans un Web Worker Pyodide isolé avec fichiers/imports locaux.
- Les projets framework côté serveur (Django/DRF/FastAPI/Flask/Express/Next.js) sont éditables et collaboratifs, mais ne sont **pas exécutés sur le serveur LearnEas** : aucun moteur d’exécution de code arbitraire multi-tenant n’est activé par défaut.
- Tableau blanc collaboratif avec dessin souris/tactile, couleurs, épaisseur, annulation et effacement synchronisés.
- Pour une production fiable derrière des NAT/réseaux mobiles, un **TURN** reste nécessaire. Pour des classes nombreuses, prévoir une architecture **SFU** plutôt qu'un maillage WebRTC pair-à-pair.

### Comptes & rôles
- 3 rôles : étudiant, instructeur, administrateur.
- Un étudiant peut déposer une **demande pour devenir instructeur** depuis son dashboard ; le rôle n’est accordé qu’après validation explicite par un administrateur.
- Dashboards dédiés :
  - **Étudiant** : mes cours, ma progression, mes PDF, mon profil, mes certificats.
  - **Instructeur** : back-office complet avec sidebar dédiée : aperçu, cours, PDF, formations live,
    séances, étudiants, statistiques, avis/questions, revenus/versements, messages et profil/paramètres.
    Les KPI sont navigables vers les vues détaillées. L’instructeur peut créer, modifier, publier ou
    dépublier ses contenus, suivre ses étudiants et leur progression, consulter ses ventes, configurer
    sa destination de versement, demander un retrait, répondre aux questions de cours, contrôler les
    présences des séances live et gérer son profil public ainsi que son mot de passe.
  - **Admin** : back-office complet avec sidebar dédiée : aperçu, utilisateurs, demandes instructeur, contenus, commandes,
    versements instructeurs, séances live, catégories, FAQ/avis et paramètres de la plateforme.
    L'admin peut créer/désactiver des comptes, gérer les rôles, approuver/refuser les demandes instructeur, modérer le catalogue et les avis. Tous les KPI
    sont navigables vers leur détail, les listes sont filtrables/paginées et les rapports de présence
    s'ouvrent dans une fenêtre dédiée.
    Un compte admin **technique** (`is_staff` + `is_superuser`) dispose aussi du bouton **Administration technique** vers Django Admin ; ce privilège n’est pas accordé automatiquement aux simples admins applicatifs.


### Paramétrage administrateur

Depuis **Tableau de bord → Administration → Paramètres**, un administrateur peut modifier sans
redéploiement :

- le nom de la plateforme et l'email d'assistance ;
- l'ouverture/fermeture des nouvelles inscriptions ;
- l'autorisation des demandes pour devenir instructeur ;
- le pourcentage de commission de la plateforme sur les nouvelles ventes ;
- le montant minimum autorisé pour une demande de versement instructeur.
- les devises actives, leur taux par rapport à l’EUR et la devise de checkout par défaut ;
- les passerelles Stripe / YouCan Pay / GeniusPay / **CinetPay Mobile Money** / paiement manuel, leurs devises compatibles et leur mode test ;
- un diagnostic d’envoi email et un diagnostic non transactionnel de chaque passerelle de paiement.

Les paramètres financiers enregistrés en base remplacent les valeurs d'environnement pour les
nouvelles opérations. Les anciennes lignes de vente gardent les montants de commission déjà
enregistrés afin de préserver l'historique comptable.

Une demande instructeur reste au statut **En attente** tant qu’un administrateur ne l’a pas approuvée ; le simple dépôt ne change plus le rôle du compte.

### Autres
- Avis & notes (étoiles) sur cours et PDF, recalcul automatique de la moyenne.
- FAQ, page instructeurs, page contact.
- Design responsive (mobile / tablette / desktop).

---

## 🧩 Projets pratiques & portfolio professionnel

LearnEas permet désormais à un instructeur d’ajouter des projets évalués aux cours. Un projet peut être requis pour l’obtention du certificat, conserver l’historique des remises et être corrigé avec note et feedback. Une réalisation approuvée peut ensuite être publiée dans un portfolio public avec un badge de vérification LearnEas ; les preuves de validation sont figées côté serveur et ne peuvent pas être altérées par l’apprenant. Les réalisations externes peuvent aussi être ajoutées, sans badge vérifié.

La page publique du portfolio n’expose ni email ni téléphone, et les fichiers de remise restent privés. Voir `docs/PROJECTS_PORTFOLIO.md`.

## 🚀 Lancer le projet

### Option A — Docker (recommandé, tout est orchestré)

Prérequis : [Docker](https://docs.docker.com/get-docker/) et Docker Compose v2.

```bash
cp .env.docker.example .env      # profil local : DEBUG=True
docker compose up -d --build
```

Cela démarre 6 services orchestrés ensemble :

| Service | Rôle |
|---|---|
| `db` | PostgreSQL 16 |
| `redis` | Cache + broker Celery |
| `backend` | Django + Gunicorn (API REST) |
| `celery_worker` | Tâches asynchrones (emails, etc.) |
| `frontend` | Next.js en mode standalone |
| `nginx` | Reverse proxy unique — point d'entrée sur `http://localhost` |

Au premier lancement :
```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_demo      # données de démo (facultatif)
docker compose exec backend python manage.py createsuperuser # votre compte admin
```
(ou passez `SEED_DEMO=true` dans `.env` pour que ce soit fait automatiquement au démarrage).

L'application est alors disponible sur **http://localhost** (frontend), l'API sur
**http://localhost/api**, l'admin Django sur **http://localhost/admin**.

Un `Makefile` simplifie les commandes usuelles : `make up`, `make logs`, `make migrate`,
`make seed`, `make superuser`, `make backend-shell`, `make down`. Voir `make help`.

**Mode développement (hot-reload)** — code monté en volume, rechargement automatique :
```bash
make dev
# ou : docker compose -f docker-compose.dev.yml up --build
```
Backend sur http://localhost:8000, frontend sur http://localhost:3000, sans nginx devant.

### Option B — Installation manuelle (sans Docker)

#### 1. Backend (Django)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # à adapter si besoin (SECRET_KEY, base de données...)

python manage.py migrate
python manage.py seed_demo        # crée des données de démonstration + un admin
python manage.py runserver        # http://localhost:8000
```

Les identifiants complets des comptes de test sont documentés dans la section
[**Comptes de test / démonstration**](#-comptes-de-test--démonstration) ci-dessus.

Voir [`CHANGELOG.md`](./CHANGELOG.md) pour le détail des données de démonstration.

Admin Django : http://localhost:8000/admin
Documentation API (Swagger) : http://localhost:8000/api/docs

#### 2. Frontend (Next.js)

```bash
cd frontend
npm install
cp .env.local.example .env.local  # NEXT_PUBLIC_API_URL=http://localhost:8000/api
npm run dev                       # http://localhost:3000
```

---

## 🗄️ Modèle de données (résumé)

| App | Modèles clés |
|---|---|
| `accounts` | `User` (rôle admin/instructor/student), `PlatformSettings`, `InstructorApplication` |
| `catalog` | `Category`, `Course`, `Section`, `Lesson`, `PDFResource` (inclus dans un cours), `PDFProduct` (vendu seul) |
| `formations` | `InteractiveFormation`, `FormationSession`, `FormationEnrollment`, `FormationAttendance`, `FormationSignal` |
| `enrollments` | `CourseEnrollment`, `LessonProgress`, `PDFPurchase`, `Wishlist`, `Certificate` |
| `payments` | `Currency`, `PaymentGateway`, `Order`, `OrderItem`, `FormationSeatReservation`, `PayoutProfile`, `InstructorPayout` |
| `reviews` | `Review`, `LessonComment` |
| `faq` | `FAQ` |
| `chat` | `ChatMessage` |

---

## 🔒 Sécurité & production

> **Important :** le Docker local démarre avec `DEBUG=True` et la clé de développement
> `dev-secret-key-change-me`. Ne réutilisez jamais cette clé en production. Sur Railway, définissez
> explicitement `DEBUG=False` et une `SECRET_KEY` forte (au moins 32 caractères). Le backend
> refusera volontairement de démarrer si une clé de développement est utilisée avec `DEBUG=False`.


La v28 applique notamment les garde-fous suivants : JWT pour l’API, rotation/blacklist des refresh tokens,
throttling Redis partagé entre workers, mots de passe validés par Django, médias pédagogiques privés
servis via URL signée + `X-Accel-Redirect`, Stripe Checkout + webhook signé, réservation temporaire
atomique des places live, contrôles de rôles côté API, CSP/en-têtes nginx, secrets faibles et
`ALLOWED_HOSTS=*` refusés lorsque `DEBUG=False`, documentation API uniquement en développement,
backend/Celery exécutés sous utilisateur non privilégié après bootstrap.

Avant exposition Internet, configurez obligatoirement :

1. `SECRET_KEY` aléatoire long, `DEBUG=False`, `ALLOWED_HOSTS` et HTTPS réel (`USE_HTTPS=True`).
2. Les clés **live et test séparées** des prestataires activés. Pour Stripe, configurez `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` et `STRIPE_TEST_SECRET_KEY` / `STRIPE_TEST_WEBHOOK_SECRET` selon les environnements. Pour YouCan Pay, le token utilisé par LearnEas doit autoriser la création et la consultation des factures ; renseignez un token sandbox séparé si votre compte en fournit un. Pour GeniusPay, renseignez les couples clé/secret et secrets webhook distincts sandbox/live.
3. Les URLs webhook HTTPS : `/api/payments/stripe/webhook/` et `/api/payments/geniuspay/webhook/`. YouCan Pay est réconcilié côté serveur en relisant l’état de la facture lors du retour/vérification.
4. Un SMTP réel pour les emails transactionnels puis utilisez **Admin → Paramètres → Test email**.
5. Un serveur TURN pour fiabiliser les classes WebRTC sur réseaux mobiles/NAT restrictifs.
6. Un stockage objet/CDN pour les médias et segments HLS ; sur Railway activez `USE_S3=True` et `REQUIRE_REMOTE_MEDIA=True` afin que les paquets HLS v43 survivent aux redéploiements.

Les limitations et priorités restantes sont détaillées dans [`AUDIT.md`](./AUDIT.md).

---

## 🧪 Validation et stratégie de tests

Le dépôt contient des tests Django/DRF de régression couvrant notamment authentification, permissions,
achats/droits d’accès, médias privés, live, certificats, avis, messagerie et finances instructeur.
La CI (`.github/workflows/ci.yml`) exécute dans un environnement connecté :

```text
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate --noinput
python manage.py test
npm ci
npm run audit:mobile
npm run build
docker compose config -q
```

Dans l’environnement de génération de cette archive v9, les contrôles effectivement exécutés sont :
parsing AST de tous les fichiers Python, syntaxe shell de l’entrypoint, parsing TypeScript/TSX,
résolution des imports locaux, audit mobile statique, validation YAML des Compose/CI et cohérence
statique des dépendances de migrations. Le véritable build Next.js et la suite Django nécessitent les
dépendances npm/pip et sont donc laissés à la CI/Docker de la machine cible.

---

## 📁 Prochaines étapes suggérées

- Notifications (email + in-app) sur achat, nouveau commentaire, réponse instructeur.
- Recherche full-text avancée (Algolia/Meilisearch), comme dans le projet Laravel d'origine.
- Chat en direct temps réel (WebSocket / Django Channels) — le modèle `ChatMessage` est déjà prêt.
- Stockage objet/CDN pour les médias volumineux et supervision de la qualité des séances WebRTC.
- Système d'abonnement "Premium" (accès illimité à un catalogue) en complément de l'achat à l'unité.

Bon lancement avec **LearnEas** 🚀

### Authentification API et CSRF

L’API LearnEas (`/api/...`) utilise JWT (`Authorization: Bearer ...`) et **pas** les sessions Django. Cette séparation évite qu’un cookie de session créé par `/admin/` impose à tort un jeton CSRF aux endpoints publics comme `/api/auth/login/` ou `/api/auth/register/`. Le Django Admin continue, lui, à utiliser les sessions et la protection CSRF standard de Django.


## Exécution de code dans les séances live

La salle live peut exécuter JavaScript dans une iframe sandboxée et Python dans le navigateur via Pyodide/WebAssembly (version épinglée `0.27.7` chargée depuis jsDelivr). HTML et CSS disposent d'un aperçu direct. Java, C et C++ restent éditables et synchronisés mais ne sont pas exécutés côté serveur, afin de ne pas exposer le backend à l'exécution arbitraire de code. En environnement à accès Internet filtré, autoriser `https://cdn.jsdelivr.net` ou héberger les ressources Pyodide en interne.

### Paiement test local

En développement, `TEST_PAYMENTS_ENABLED=True` expose dans le checkout un moyen **Paiement test LearnEas**. Il simule un paiement réussi sans contacter Stripe, YouCan Pay ou GeniusPay et accorde les accès comme après une transaction confirmée.

En production, imposez :

```env
DEBUG=False
TEST_PAYMENTS_ENABLED=False
```

Le mode test interne ne doit jamais être activé sur un environnement public.


## Compatibilité vidéo

LearnEas ne se fie plus uniquement à l'extension du fichier. Lors d'un upload MP4/WebM/MOV/M4V, le backend inspecte les pistes avec `ffprobe`. Un MP4 déjà encodé en **H.264/AAC yuv420p** est conservé sans réencodage ; un fichier utilisant HEVC/H.265, H.264 10-bit ou un autre codec moins compatible est automatiquement normalisé par `ffmpeg` vers **MP4 H.264/AAC + faststart**. Les médias privés conservent le support HTTP Range. Les URLs HTTPS directes ainsi que YouTube/Vimeo restent prises en charge.

Pour réparer les vidéos uploadées avant cette version :

```bash
# Voir ce qui doit être converti, sans modification
docker compose exec backend python manage.py normalize_course_videos --dry-run

# Convertir toutes les anciennes vidéos incompatibles
docker compose exec backend python manage.py normalize_course_videos
```

L'administrateur et l'instructeur propriétaire disposent aussi d'un bouton **Réparer cette vidéo** dans le lecteur. La conversion est envoyée au worker Celery et le lecteur se recharge automatiquement quand le fichier H.264/AAC est prêt.

### Streaming adaptatif / faible connexion (v43)

Après l'upload d'un fichier vidéo, LearnEas prépare automatiquement en arrière-plan un paquet HLS privé. Selon la résolution d'origine, le worker produit jusqu'à **240p, 360p, 480p et 720p** ainsi qu'une playlist **audio seule ~48 kb/s**. Le fichier MP4 normalisé reste conservé comme fallback.

Le lecteur propose :

- **Auto** : adaptation dynamique à la bande passante ;
- **Économie de données** : Auto plafonné à 360p, mémorisé dans le navigateur ;
- sélection manuelle de la qualité disponible ;
- **Audio uniquement** : pas de téléchargement des segments vidéo, uniquement l'audio faible débit ;
- conservation de la position de lecture lors du passage vidéo ↔ audio.

Pour préparer les vidéos déjà présentes avant v43 :

```bash
docker compose exec backend python manage.py prepare_course_streaming
```

Pour forcer une régénération complète :

```bash
docker compose exec backend python manage.py prepare_course_streaming --force
```

Les manifests et segments sont privés : le frontend ne reçoit que des URL signées expirantes. En Docker local les segments passent par nginx/X-Accel-Redirect ; en production avec `USE_S3=True`, ils utilisent le stockage objet présigné.
Si le frontend est sur **Vercel** et les segments sur un domaine S3/R2 distinct, définissez aussi `NEXT_PUBLIC_MEDIA_ORIGIN=https://votre-cdn.example.com` au build frontend et autorisez les requêtes `GET`/`HEAD` depuis le domaine LearnEas dans la politique CORS du bucket. Cela permet à hls.js de charger les segments sans élargir inutilement la CSP à tous les domaines.

Variables disponibles :

```env
HLS_STREAMING_ENABLED=True
HLS_MAX_HEIGHT=720
HLS_SEGMENT_SECONDS=6
HLS_TRANSCODE_TIMEOUT_SECONDS=7200
HLS_TRANSCODE_PRESET=veryfast
HLS_AUDIO_ONLY_BITRATE=48k
```

## WhatsApp transactionnel (v44)

LearnEas peut envoyer des confirmations de paiement, rappels de live, relances de cours inactifs et notifications de certificat via Meta WhatsApp Cloud API. Le canal est **opt-in**, les secrets restent côté backend, et un mode simulation permet les tests locaux sans envoi réel. Voir `docs/WHATSAPP.md` pour les templates, variables d'environnement, webhook et configuration Railway/Celery Beat.

