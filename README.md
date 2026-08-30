# LearnEas

> **Mise à jour majeure** — voir [`CHANGELOG.md`](./CHANGELOG.md) pour le détail des corrections de
> sécurité, du module Formation Interactive, de l'orientation Afrique (Mobile Money, pays africains)
> et de toutes les vérifications effectuées.

Plateforme de formation en ligne — refonte du projet PFE "Gestion de la formation en ligne" (Laravel)
en **Django REST Framework + Next.js**, avec un nouveau paradigme :

> On n'achète plus une vidéo isolée. On achète un **cours complet** (playlist entière avec toutes ses
> vidéos organisées en modules) ou un **PDF** — vendu seul ou inclus dans un cours.

Style visuel inspiré de Coursera / Udemy, avec une identité propre (palette verte, cartes arrondies,
dashboards dédiés par rôle).

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
- Lecteur vidéo unifié : contrôles natifs complets, ±10 s, recommencer, volume/mute, vitesse 0,5× à 2×, boucle, sous-titres WebVTT, Picture-in-Picture, plein écran, nouvel onglet, téléchargement et raccourcis clavier (K/Espace, J/L, flèches, M, F).
- Lecteur PDF unifié : barre native du navigateur (pages, recherche, zoom, miniatures selon navigateur), plein écran/modal, impression, nouvel onglet et téléchargement.
- Les leçons acceptent désormais un fichier de sous-titres `.vtt` et une transcription.
- **Apprenant → Mes certificats** : registre personnel, filtres, affichage, impression/PDF, partage et vérification publique.
- **Instructeur → Certificats** : règles par cours/formation, seuil de progression ou de présence réelle, délivrance automatique/manuelle ou groupée, validité, apparence, signataire, préfixe, registre, révocation et réémission.
- **Admin → Certificats** : registre global, vérification/révocation/réémission, délivrance groupée ou forcée et paramètres globaux + surcharge par contenu.
- La présence aux formations live est calculée à partir du temps réellement enregistré dans les séances, et non d'une simple case « présent ».
- `seed_demo` délivre un certificat d'exemple à **Fatou Ndiaye** sur le cours Django pour tester immédiatement l'onglet « Mes certificats ».

### Catalogue
- Cours = **playlist complète** : sections → leçons vidéo, durée totale et nombre de vidéos calculés
  automatiquement (signal Django).
- PDF **inclus dans un cours** (ressource additionnelle) ET PDF **vendus seuls** (catalogue indépendant).
- Catégories avec icônes (lucide-react), niveaux (débutant/intermédiaire/expert), langue, prix, promo.
- Recherche, filtres (catégorie, niveau, gratuit), tri (récent, prix, note, popularité).

### Achat & accès
- Panier (persisté en local), checkout Stripe hébergé et confirmation par webhook signé. Les moyens non intégrés (PayPal/Mobile Money) restent explicitement indisponibles au lieu d’être simulés.
- Une commande peut contenir plusieurs cours et PDF en même temps.
- **Le contenu vidéo/PDF est verrouillé côté API tant que l'achat n'est pas confirmé** (pas juste côté
  affichage) — vérifié par tests réels (voir plus bas).
- Leçons en "aperçu gratuit" consultables sans achat.

### Apprentissage
- Espace d'apprentissage dédié (`/learn/[slug]`) : lecteur vidéo, sidebar curriculum, suivi de
  progression leçon par leçon, onglet ressources PDF, onglet discussion (base posée).
- Barre de progression par cours, calcul automatique du `%` de complétion.
- **Certificat configurable** : délivrance automatique à partir du seuil défini sur le cours, ou du taux de présence réel pour une formation live ; page imprimable/enregistrable en PDF et vérification publique par code.

### Salle live / visioconférence
- Salle WebRTC interne avec caméra et microphone, présence réelle et suivi du temps de connexion.
- Partage d'écran natif navigateur, chat de séance, levée de main et panneau des participants.
- Choix du microphone et de la caméra pendant la séance, ainsi que mode plein écran.
- Pour l'organisateur : commandes de modération (couper micro/caméra, retirer un participant).
- Partage de fichiers de séance avec téléchargement authentifié et limite de 20 Mo par fichier.
- Enregistrement local côté organisateur de la grille vidéo et du mix audio disponibles au moment de l'enregistrement ; le fichier WebM est téléchargé sur le poste de l'organisateur et n'est pas stocké automatiquement sur le serveur.
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


### Paramétrage administrateur

Depuis **Tableau de bord → Administration → Paramètres**, un administrateur peut modifier sans
redéploiement :

- le nom de la plateforme et l'email d'assistance ;
- l'ouverture/fermeture des nouvelles inscriptions ;
- l'autorisation des demandes pour devenir instructeur ;
- le pourcentage de commission de la plateforme sur les nouvelles ventes ;
- le montant minimum autorisé pour une demande de versement instructeur.

Les paramètres financiers enregistrés en base remplacent les valeurs d'environnement pour les
nouvelles opérations. Les anciennes lignes de vente gardent les montants de commission déjà
enregistrés afin de préserver l'historique comptable.

Une demande instructeur reste au statut **En attente** tant qu’un administrateur ne l’a pas approuvée ; le simple dépôt ne change plus le rôle du compte.

### Autres
- Avis & notes (étoiles) sur cours et PDF, recalcul automatique de la moyenne.
- FAQ, page instructeurs, page contact.
- Design responsive (mobile / tablette / desktop).

---

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
| `payments` | `Order`, `OrderItem`, `FormationSeatReservation`, `PayoutProfile`, `InstructorPayout` |
| `reviews` | `Review`, `LessonComment` |
| `faq` | `FAQ` |
| `chat` | `ChatMessage` |

---

## 🔒 Sécurité & production

> **Important :** le Docker local démarre avec `DEBUG=True` et la clé de développement
> `dev-secret-key-change-me`. Ne réutilisez jamais cette clé en production. Sur Railway, définissez
> explicitement `DEBUG=False` et une `SECRET_KEY` forte (au moins 32 caractères). Le backend
> refusera volontairement de démarrer si une clé de développement est utilisée avec `DEBUG=False`.


La v9 applique les garde-fous suivants : JWT pour l’API, rotation/blacklist des refresh tokens,
throttling Redis partagé entre workers, mots de passe validés par Django, médias pédagogiques privés
servis via URL signée + `X-Accel-Redirect`, Stripe Checkout + webhook signé, réservation temporaire
atomique des places live, contrôles de rôles côté API, CSP/en-têtes nginx, secrets faibles et
`ALLOWED_HOSTS=*` refusés lorsque `DEBUG=False`, documentation API uniquement en développement,
backend/Celery exécutés sous utilisateur non privilégié après bootstrap.

Avant exposition Internet, configurez obligatoirement :

1. `SECRET_KEY` aléatoire long, `DEBUG=False`, `ALLOWED_HOSTS` et HTTPS réel (`USE_HTTPS=True`).
2. `STRIPE_SECRET_KEY` **et** `STRIPE_WEBHOOK_SECRET`; configurez chez Stripe l’URL
   `https://votre-domaine/api/payments/stripe/webhook/`.
3. Un SMTP réel pour les emails transactionnels.
4. Un serveur TURN pour fiabiliser les classes WebRTC sur réseaux mobiles/NAT restrictifs.
5. Un stockage objet/CDN et idéalement HLS adaptatif pour les vidéos importantes ; le disque local
   reste adapté au développement et aux petites installations.
6. Un vrai prestataire Mobile Money avant d’afficher Orange Money/MTN/Wave comme moyens actifs.

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

