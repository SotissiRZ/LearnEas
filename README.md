# LearnEas

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
├── backend/     Django 5 + Django REST Framework (API JSON, JWT, admin)
└── frontend/    Next.js 14 (App Router) + TypeScript + Tailwind CSS
```

Les deux projets communiquent exclusivement via l'API REST (`/api/...`). Le frontend n'accède jamais
directement à la base de données.

---

## ✅ Fonctionnalités implémentées (testées de bout en bout)

### Catalogue
- Cours = **playlist complète** : sections → leçons vidéo, durée totale et nombre de vidéos calculés
  automatiquement (signal Django).
- PDF **inclus dans un cours** (ressource additionnelle) ET PDF **vendus seuls** (catalogue indépendant).
- Catégories avec icônes (lucide-react), niveaux (débutant/intermédiaire/expert), langue, prix, promo.
- Recherche, filtres (catégorie, niveau, gratuit), tri (récent, prix, note, popularité).

### Achat & accès
- Panier (persisté en local), checkout (Stripe/PayPal — squelette d'intégration, à brancher en prod).
- Une commande peut contenir plusieurs cours et PDF en même temps.
- **Le contenu vidéo/PDF est verrouillé côté API tant que l'achat n'est pas confirmé** (pas juste côté
  affichage) — vérifié par tests réels (voir plus bas).
- Leçons en "aperçu gratuit" consultables sans achat.

### Apprentissage
- Espace d'apprentissage dédié (`/learn/[slug]`) : lecteur vidéo, sidebar curriculum, suivi de
  progression leçon par leçon, onglet ressources PDF, onglet discussion (base posée).
- Barre de progression par cours, calcul automatique du `%` de complétion.
- **Certificat de fin de formation** émis automatiquement à 100 %, page imprimable dédiée.

### Comptes & rôles
- 3 rôles : étudiant, instructeur, administrateur.
- Un étudiant peut devenir instructeur directement depuis son dashboard.
- Dashboards dédiés :
  - **Étudiant** : mes cours, ma progression, mes PDF, mon profil, mes certificats.
  - **Instructeur** : aperçu (stats), gestion des cours (créer/ajouter sections+vidéos/publier),
    gestion des PDF (créer + upload).
  - **Admin** : vue d'ensemble des commandes/revenus, lien direct vers l'admin Django (gestion
    complète utilisateurs/contenu).

### Autres
- Avis & notes (étoiles) sur cours et PDF, recalcul automatique de la moyenne.
- FAQ, page instructeurs, page contact.
- Design responsive (mobile / tablette / desktop).

---

## 🚀 Lancer le projet en local

### 1. Backend (Django)

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

Comptes créés par `seed_demo` :
- Admin : `admin@learneas.com` / `admin1234`
- Instructeur : `sarah@learneas.com` / `instructor1234`

Admin Django : http://localhost:8000/admin
Documentation API (Swagger) : http://localhost:8000/api/docs

### 2. Frontend (Next.js)

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
| `accounts` | `User` (rôle admin/instructor/student) |
| `catalog` | `Category`, `Course`, `Section`, `Lesson`, `PDFResource` (inclus dans un cours), `PDFProduct` (vendu seul) |
| `enrollments` | `CourseEnrollment`, `LessonProgress`, `PDFPurchase`, `Wishlist` |
| `payments` | `Order`, `OrderItem` |
| `reviews` | `Review`, `LessonComment` |
| `faq` | `FAQ` |
| `chat` | `ChatMessage` |

---

## 🔒 Sécurité & production — à faire avant mise en ligne

Ce livrable est une base **fonctionnelle et testée**, mais quelques points sont volontairement
simplifiés pour rester un point de départ clair. À finaliser avant lancement public :

1. **Paiement réel** : `apps/payments/views.py::CheckoutView` contient un webhook simplifié qui
   confirme immédiatement la commande. En production, intégrer réellement Stripe PaymentIntents
   (ou PayPal Orders API) et déplacer la confirmation vers un vrai webhook signé.
2. **Upload vidéo** : actuellement `video_url` (lien externe/CDN) ou `video_file` (upload direct sur
   le serveur). Pour la production, brancher un stockage objet (S3, Backblaze, Bunny Stream) via
   `django-storages`, déjà présent dans `requirements.txt`.
3. **Recherche avancée** : le cahier des charges d'origine mentionnait Algolia. La recherche actuelle
   utilise le `SearchFilter` de DRF (suffisant pour démarrer). Brancher Algolia/Meilisearch plus tard
   si le catalogue grossit.
4. **Emails transactionnels** : confirmation de commande, réinitialisation de mot de passe — à
   brancher (Django email backend + templates).
5. **`SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS`, base PostgreSQL** : à configurer via `.env` avant
   déploiement (le projet est déjà prêt pour PostgreSQL, voir `DB_ENGINE` dans `.env.example`).
6. **Upload de fichiers depuis le dashboard instructeur** : le formulaire de création de cours ajoute
   des vidéos par URL pour aller vite ; un upload multipart de fichier vidéo direct (comme pour les
   PDF) est facile à ajouter sur le même modèle que `NewPdfPage`.

---

## 🧪 Ce qui a été réellement testé (pas seulement écrit)

- Build de production Next.js : **23 routes, 0 erreur TypeScript**.
- `python manage.py check` / `makemigrations` / `migrate` : **0 erreur**.
- Tunnel complet : inscription → login JWT → ajout panier → checkout → confirmation paiement →
  déverrouillage réel de la playlist (vérifié via l'API, pas supposé).
- Achat d'un PDF seul → déverrouillage du fichier.
- Progression leçon par leçon jusqu'à 100 % → `completed = true` → **certificat auto-émis**.
- Système d'avis (review) créé et moyenne recalculée.
- Deux bugs réels détectés et corrigés pendant le développement (pagination de `/categories/` non
  attendue par le frontend ; JSX dupliqué dans le dashboard étudiant).

---

## 📁 Prochaines étapes suggérées

- Notifications (email + in-app) sur achat, nouveau commentaire, réponse instructeur.
- Recherche full-text avancée (Algolia/Meilisearch), comme dans le projet Laravel d'origine.
- Chat en direct temps réel (WebSocket / Django Channels) — le modèle `ChatMessage` est déjà prêt.
- Upload vidéo direct + génération automatique de la durée (ffprobe) au lieu de la saisir à la main.
- Système d'abonnement "Premium" (accès illimité à un catalogue) en complément de l'achat à l'unité.

Bon lancement avec **LearnEas** 🚀
