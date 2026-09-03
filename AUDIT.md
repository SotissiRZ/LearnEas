# Audit technique LearnEas — v28

Date : 2026-08-31

## Résumé exécutif

La v28 reprend l’audit sécurité, intégrité métier, paiements, visioconférence, stockage, performance,
responsive et déploiement Railway/Vercel. Les défauts applicatifs identifiés pendant l’audit ont été
corrigés dans le code. Les points restant à traiter sont des **contraintes d’infrastructure ou de montée
en charge**, listées explicitement à la fin de ce document.

## Corrections de sécurité

- API applicative authentifiée par JWT ; Django Admin conserve session + CSRF.
- Access tokens liés à l’empreinte du mot de passe : un changement/réinitialisation invalide les anciens accès.
- Rotation + blacklist des refresh tokens ; logout serveur et révocation de tous les refresh après changement de mot de passe.
- Renouvellement JWT sérialisé côté frontend, également appliqué aux uploads et téléchargements.
- Redirections `next=` limitées strictement à l’origine frontend sur login **et inscription**.
- Email/username de profil non modifiables via l’endpoint utilisateur générique afin de préserver l’identité des invitations et sessions.
- Validation Django des mots de passe, y compris création de compte par un administrateur.
- Throttling Redis spécialisé pour auth, reset, checkout, médias, diagnostics admin, webhooks et polling/signalisation live.
- Payloads live bornés : taille globale, chat, projets de code, fichiers et tableau blanc.
- Modération live réservée à l’organisateur ; une séance terminée refuse les nouveaux signaux métier.
- Fichiers pédagogiques et fichiers de réunion privés protégés ; accès local via `X-Accel-Redirect` interne et URLs S3 présignées courtes en stockage distant.
- Uploads bornés par taille/type et métadonnées PDF/vidéo vérifiées côté serveur.
- v29 : uploads vidéo jusqu’à 2 Go par défaut côté Docker local, limites configurables côté Django et validation navigateur avant transfert ; les gros fichiers sont spoulés sur disque plutôt qu’en mémoire.
- v29 : lecteur PDF média privé vérifié contre les blocages CSP/X-Frame ; seul le point d’accès média signé est embeddable par les origines frontend autorisées.
- CSP, `nosniff`, frame deny, Referrer-Policy et Permissions-Policy sur Nginx et Next.js/Vercel.
- CSP Next.js ajoute dynamiquement l’origine `NEXT_PUBLIC_API_URL` quand Railway et Vercel sont sur des domaines distincts.
- Pyodide/Python exécuté dans un **Web Worker** séparé sans accès au DOM, localStorage ou JWT ; JavaScript/HTML/CSS exécutés dans des iframes sandboxées.
- Aucune exécution serveur arbitraire de projets Django/Next/Express : ces templates sont éditables/collaboratifs uniquement.
- Garde-fous production : SECRET_KEY faible et `ALLOWED_HOSTS=*` refusés avec `DEBUG=False`; possibilité d’exiger un stockage média distant.
- HSTS configurable lorsque `USE_HTTPS=True`.

## Paiements et intégrité financière

- Configuration dynamique des devises et passerelles par l’admin.
- Drivers intégrés : Stripe, YouCan Pay, GeniusPay, paiement manuel.
- Secrets uniquement dans l’environnement serveur, jamais en base ni dans le frontend.
- Mode sandbox/live **réellement relié aux credentials** ; l’environnement utilisé est figé sur chaque commande (`provider_sandbox`).
- Le checkout valide devise, moyen de paiement actif, support de devise et présence des clés avant transaction.
- Les acquisitions gratuites ne dépendent d’aucune passerelle externe.
- Création de commande, lignes et réservations de places sous transaction ; rollback si la création du checkout distant échoue.
- Réservation atomique des dernières places d’une formation payante.
- Confirmation client = réconciliation serveur : statut, montant et devise vérifiés auprès du prestataire.
- Stripe : signature webhook, référence de session, utilisateur, montant/devise et `payment_status=paid` vérifiés.
- GeniusPay : HMAC SHA-256, fenêtre anti-rejeu 5 min, cache anti-duplication, environnement sandbox/live, référence, utilisateur, montant/devise vérifiés.
- Transitions de commandes et versements limitées ; une commande externe ne peut pas être forcée payée en production par le frontend.
- Snapshot commission/instructeur enregistré sur chaque ligne de vente afin de préserver l’historique financier.
- Les devises sont limitées à 0–2 décimales. MAD reste la devise comptable de base (taux 1, toujours active) ; la devise de checkout par défaut peut être différente.
- Diagnostics admin non transactionnels pour email et connexions prestataires, avec throttling dédié. Les secrets test/live ne se remplacent jamais mutuellement.

## Permissions et contenu instructeur

- Un instructeur peut créer/modifier/publier ses cours, sections, leçons, ressources PDF, PDF autonomes et formations.
- `featured` reste une décision éditoriale admin : si un formulaire instructeur envoie `featured=false` ou `true`, le champ est ignoré au lieu de faire échouer la création.
- Querysets de gestion sont filtrés au propriétaire ; permissions objet empêchent la modification du contenu d’un autre instructeur.
- Django Admin technique reste réservé aux comptes admin explicitement `is_staff` + `is_superuser`; les journaux financiers y sont en lecture seule afin de ne pas contourner les workflows de paiement/versement.
- Médias verrouillés ne sont pas divulgués dans les serializers aux apprenants non inscrits.
- Tests de régression ajoutés pour création de cours/PDF instructeur et champ `featured`.

## Réunion / collaboration

- Salle fixe plein viewport, panneaux et commandes repliables pour privilégier l’espace de travail.
- WebRTC caméra/micro, partage écran, choix des périphériques, chat, présence, levée de main, modération, fichiers et invitation ponctuelle par email.
- Invité non inscrit limité à la séance : aucune inscription/certification implicite.
- Durées de présence bornées à la fenêtre réelle de séance afin d’éviter de compter une déconnexion oubliée comme plusieurs heures de présence.
- Tableau blanc collaboratif borné et synchronisé.
- Mini-IDE **multi-fichiers** : fichiers/dossiers logiques, POO et templates React, Next.js, Django, DRF, FastAPI, Flask, Express.
- Python multi-fichiers exécuté localement via Pyodide avec imports locaux ; thèmes/coloration syntaxique et console redimensionnable.

## Performance

- `select_related`/`prefetch_related` ajoutés aux listes critiques et suppression de plusieurs N+1.
- Index DB sur chemins catalogue, commandes, formations, invitations et réservations.
- Agrégations SQL pour KPI/finance/notes au lieu d’agrégations côté client.
- Médias privés servis par Nginx en local ; stockage objet recommandé en production.
- Docker Compose attend les healthchecks backend/frontend avant de démarrer les dépendants, ce qui évite les 502 pendant les migrations.
- Healthchecks disposent d’une période de démarrage adaptée.

## Vérifications de livraison

Contrôles réellement exécutés avant la création de l’archive v28 :

- **Python** : 124 fichiers analysés avec `ast.parse`, **0 erreur syntaxique**.
- **TypeScript / TSX** : 95 fichiers analysés avec le parseur TypeScript, **0 erreur de parsing**.
- **Références TypeScript locales** : passage `tsc --noEmit` sans dépendances installées ; **0 erreur TS2304 / TS2552** (identifiants locaux introuvables). Les autres diagnostics proviennent de l’absence de React/Next et de leurs types dans `node_modules`.
- **Audit mobile** : 88 fichiers inspectés par `npm run audit:mobile`, **aucune alerte bloquante**.
- **Compose YAML** : `docker-compose.yml` et `docker-compose.dev.yml` parsés avec succès ; dépendances/healthchecks présents.
- **JSON frontend** : `package.json` et `package-lock.json` valides.
- **Migrations** : aucun numéro dupliqué et aucune dépendance locale de migration manquante détectée statiquement.
- **Noms d’index/contraintes explicitement nommés** : aucun nom supérieur à 30 caractères après correction de la réservation de place ; la migration `payments/0008` renomme aussi l’ancien nom sur les bases PostgreSQL déjà créées.
- **Hygiène dépôt** : aucun marqueur TODO/FIXME/HACK bloquant dans `backend/` ou `frontend/`, et aucune clé privée / clé Stripe réelle détectée par le scan heuristique.

Contrôles runtime qui **n’ont pas pu être exécutés dans l’environnement de génération** :

- `python manage.py check`, `makemigrations --check`, migrations et tests Django : le paquet Django n’est pas installé et l’environnement n’a pas d’accès réseau pour l’installer.
- `npm ci` / `npm run build` : l’installation hors ligne s’arrête car `zustand-4.5.4.tgz` n’est pas présent dans le cache npm.
- `docker compose config` / démarrage de la stack : le CLI Docker n’est pas disponible dans l’environnement de génération.

Ces contrôles doivent donc être rejoués sur la machine de livraison/CI :

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py test
npm ci
npm run audit:mobile
npm run build
docker compose config
docker compose up --build
```

## Risques résiduels / infrastructure

Ces points ne sont pas des bugs corrigibles uniquement dans le dépôt :

1. **JWT dans localStorage** : la CSP réduit le risque XSS mais un BFF avec cookies HttpOnly serait plus robuste pour une exposition à très haut risque.
2. **WebRTC P2P** : adapté aux petites classes ; pour des classes nombreuses, utiliser un SFU (LiveKit/Jitsi/mediasoup/Janus).
3. **TURN** : indispensable en production sur certains NAT/réseaux mobiles.
4. **Stockage Railway** : activer S3/R2/Backblaze/etc. et `REQUIRE_REMOTE_MEDIA=True`; le disque Railway ne doit pas être la source durable.
5. **Antivirus/CDR** : recommandé si le partage de fichiers devient ouvert à grande échelle.
6. **Exécution framework** : aucun runner serveur arbitraire n’est fourni volontairement. Pour exécuter Django/Node/Java/C++, déployer un service sandbox éphémère dédié (conteneurs isolés, quotas CPU/RAM/temps, aucun secret/réseau interne).
7. **Clés et webhooks live** : doivent être créés dans les comptes Stripe/GeniusPay/YouCan Pay et testés sur les environnements réels ; le code ne peut pas valider des credentials inexistants.

## Checklist Railway / Vercel

- [ ] `DEBUG=False`, SECRET_KEY forte, `ALLOWED_HOSTS` exact.
- [ ] HTTPS et paramètres HSTS choisis explicitement.
- [ ] PostgreSQL + Redis Railway configurés.
- [ ] S3-compatible actif, médias persistants testés.
- [ ] SMTP testé depuis l’outil Admin.
- [ ] Passerelles sandbox testées depuis l’outil Admin puis clés live configurées.
- [ ] Webhooks Stripe/GeniusPay enregistrés sur l’URL Railway HTTPS.
- [ ] `NEXT_PUBLIC_API_URL` Vercel pointe sur `/api` Railway.
- [ ] `CORS_ALLOWED_ORIGINS` contient seulement les domaines Vercel/personnalisés attendus.
- [ ] TURN testé depuis 4G/5G et réseaux d’entreprise.
- [ ] Tests Django, build Next.js et `docker compose config` réussis dans CI/l’environnement de livraison.
- [ ] Sauvegardes PostgreSQL et bucket média restaurées au moins une fois en environnement de test.

## Correctif média v29 — vérifications ciblées

- Python : compilation syntaxique de tout `backend/` réussie.
- Frontend : parsing des 95 fichiers TS/TSX réussi ; `next.config.js` charge sans erreur.
- Docker Compose : `docker-compose.yml` et `docker-compose.dev.yml` valides en YAML.
- Nginx : `nginx -t` réussi sur la configuration v29.
- Test d'intégration Nginx simulant `X-Accel-Redirect` : le PDF privé est servi en `application/pdf`, `SAMEORIGIN`, `frame-ancestors 'self'` et avec support des requêtes Range.
- Les tests Django complets restent à rejouer dans l'image Docker, car Django n'est pas installé dans l'environnement de packaging actuel.


## v37 — espace de lecture des cours

- Lecteur repensé autour d'un workspace de formation : sommaire repliable, progression, navigation précédent/suivant, autoplay, reprise au dernier timestamp, transcription recherchable, carnet privé, Q&R et ressources.
- Les vidéos restent non téléchargeables par l'interface (`nodownload`, pas de lien source, pas de bouton download) ; le carnet exporte uniquement du texte de notes personnelles.
- Le carnet est stocké côté backend et filtré strictement par `request.user`; un autre apprenant reçoit 404 sur une note qui ne lui appartient pas.
- La position de reprise est distincte du temps maximal visionné (`last_position_seconds` vs `watched_seconds`) pour permettre de revenir en arrière sans fausser le suivi.
- Le client synchronise la position environ toutes les 15 secondes et lors d'une pause, ce qui reste largement sous le quota authentifié courant.
- Validation statique effectuée : 129 fichiers Python parsés sans erreur et 100 fichiers TypeScript/TSX transpilés sans erreur de syntaxe.
- Les tests Django ajoutés doivent être exécutés dans l'environnement Docker du projet après migration, les dépendances Django n'étant pas installées dans l'environnement de génération de l'archive.
