# Audit v75 — Recruiter Workspace, ATS & marque employeur

- Refonte de l'espace entreprise en workspace recruteur multi-onglets : vue d'ensemble, offres, candidatures, vivier et marque employeur.
- Branding entreprise enrichi : logo, bannière, couleur de marque, accroche, valeurs, avantages, zones de recrutement, LinkedIn et contact recrutement.
- Page entreprise publique avec offres ouvertes ; les compteurs excluent les offres expirées.
- Offres enrichies avec visuel, département, nombre de postes et questions de présélection.
- ATS : pipeline, notes internes, tags, notation 1–5, prochaine étape et réponses de présélection.
- Vivier : filtres pays/disponibilité/expérience et favoris persistants par entreprise.
- Migration `opportunities.0003_recruiter_workspace` additive ; aucune donnée historique supprimée.
- Contrôles statiques : 224 Python valides, 61 migrations sans cycle, 138 TS/TSX valides, tests frontend rôle employeur 6/6, performance 5/5, sécurité 4/4, audit mobile 122 fichiers sans alerte bloquante.
- Les tests Django runtime et le build Next complet restent à rejouer dans Docker/CI. Voir `docs/VALIDATION_V75.md`.

---

# Audit v63 — KalanPro AI Phase 2 · lot 1

- Ajout d'outils structurés séparant strictement lecture et mutation.
- Les outils de lecture interrogent catalogue, progression, certificats, opportunités et contenus instructeur sans exposer de données d'autres comptes.
- Les mutations IA sont transformées en propositions signées appartenant à l'utilisateur ; confirmation ou refus explicite requis.
- Validation serveur des paramètres de chaque action et contrôle de propriété instructeur.
- Expiration des confirmations après 20 minutes.
- Journal `AIActionLog` et brouillons `AIDraft` persistants ; dashboard admin et page `/assistant/drafts`.
- Function calling compatible Chat Completions ; repli sans outils si le fournisseur ne supporte pas ce format.
- Contrôles exécutés : compilation Python, parsing TS/TSX modifiés, audit mobile 119 fichiers sans alerte bloquante, sécurité frontend 4/4, YAML/JSON valides.
- 140 méthodes de tests backend présentes ; la suite Django runtime reste à exécuter dans Docker/CI.

---

# Audit v48 — Opportunités & recrutement

- Nouveau module `apps.opportunities` compilé sans erreur Python.
- 123 fichiers TypeScript/TSX analysés : 0 erreur de syntaxe et 0 import local manquant.
- `package.json`, `package-lock.json`, `tsconfig.json` et les deux Docker Compose sont syntaxiquement valides.
- Référentiel pays vérifié : 233 entrées disponibles dans les sélecteurs.
- Accès recruteur conditionné à une entreprise approuvée ; suspension = clôture des annonces publiées.
- Vivier de talents strictement opt-in et sans email/téléphone.
- CV et pièces de candidature bloqués en accès direct Nginx et servis par endpoints authentifiés.
- Candidature unique protégée par contrainte SQL + transaction ; une entreprise ne peut pas candidater à sa propre annonce.
- Snapshot des compétences, certificats actifs et projets vérifiés au moment de la candidature.
- Rémunération masquée supprimée de la représentation API publique.
- Pays validés par le référentiel KalanPro ; sélection multi-pays tactile côté candidat.
- Les candidatures retirées ne peuvent pas être réactivées par le recruteur.
- Limite actuelle : les tests Django runtime doivent être exécutés dans Docker, Django n'étant pas installé dans l'environnement de génération.

---

# Audit v47 — certificats vérifiables

- Vérification publique : numéro unique ou UUID, QR code serveur et page `noindex`.
- Confidentialité : aucun email/téléphone/identifiant de compte dans le serializer public.
- Traçabilité : snapshots compétences/projets, empreinte SHA-256, journal `CertificateEvent`, révocation motivée et réémission non destructive.
- Intégrité : contraintes SQL empêchant deux certificats `status=active` pour une même inscription, plus verrou transactionnel lors de l'émission.
- Expiration : matérialisation horaire par Celery Beat, en complément du calcul dynamique `effective_status`.
- Anti-énumération : lookup exact uniquement et throttle public dédié `certificate_verify` (300/h par défaut).
- QR : génération PNG locale vérifiée avec `qrcode==8.2`.
- Validation statique exécutée : compilation Python, 115 TS/TSX sans erreur syntaxique, audit mobile sans alerte bloquante, YAML/JSON valides, dépendances et préfixes de migrations cohérents.
- Non exécuté dans l'environnement assistant : `manage.py migrate/check/test` et build Next.js complet, faute de Django/node_modules du projet et de Docker. À exécuter dans les conteneurs du projet avant mise en production.

---

# Audit technique KalanPro — v45

Date : 2026-09-04

## Contrôles de livraison v45

La v45 ajoute les cohortes, le mentorat 1:1 et les référentiels pays/téléphone demandés pour les marchés africains francophones. Avant archivage, les contrôles statiques suivants ont été exécutés :

- compilation Python de `backend/` avec `compileall` ;
- parsing TypeScript/TSX de 111 fichiers : 0 erreur syntaxique ;
- audit responsive/mobile : 101 fichiers inspectés, aucune alerte bloquante ;
- parsing YAML de `docker-compose.yml` et JSON de la configuration frontend ;
- référentiel frontend : 233 pays/territoires, 29 marchés prioritaires, tous avec indicatif ;
- référentiel backend : 233 pays et validation des alias historiques (RDC, Côte d’Ivoire, etc.) ;
- validation E.164 côté serveur et rejet des indicatifs absents du référentiel KalanPro ;
- contrôle statique des préfixes de migrations : aucun numéro dupliqué.

Les tests Django et le build Next.js complets ne sont pas annoncés comme exécutés dans l’environnement de génération : Django et les dépendances `node_modules` n’y sont pas installés. Ils doivent être rejoués dans Docker/CI après extraction.

---

# Audit technique KalanPro — v28

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
- Throttling Redis spécialisé pour auth, reset, checkout, médias, diagnostics admin et webhooks ; la signalisation live entrante utilise désormais Channels/Redis avec ticket court et fallback HTTP borné.
- Payloads live bornés : taille globale, chat, projets de code, fichiers et tableau blanc.
- Modération live réservée à l’organisateur ; une séance terminée refuse les nouveaux signaux métier.
- Fichiers pédagogiques et fichiers de réunion privés protégés ; accès local via `X-Accel-Redirect` interne et URLs S3 présignées courtes en stockage distant.
- Uploads bornés par taille/type et métadonnées PDF/vidéo vérifiées côté serveur.
- v29 : uploads vidéo jusqu’à 2 Go par défaut côté Docker local, limites configurables côté Django et validation navigateur avant transfert ; les gros fichiers sont spoulés sur disque plutôt qu’en mémoire.
- v29 : lecteur PDF média privé vérifié contre les blocages CSP/X-Frame ; seul le point d’accès média signé est embeddable par les origines frontend autorisées.
- CSP, `nosniff`, frame deny, Referrer-Policy et Permissions-Policy sur Nginx et Next.js/Vercel. La CSP script principale est générée par requête avec nonce + `strict-dynamic` et n’autorise ni `unsafe-inline` ni `unsafe-eval` en production.
- Le runner `/code-runner/` possède une CSP séparée : JavaScript/Pyodide y sont confinés dans une iframe `sandbox="allow-scripts"` sans `allow-same-origin`, puis dans des Workers limités en temps. Les aperçus HTML/CSS n’autorisent aucun script.
- Les credentials TURN ne sont plus des variables `NEXT_PUBLIC_*`; ils sont fournis par le backend et peuvent être éphémères via secret partagé coturn.
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

1. **WebRTC P2P** : adapté aux petites classes ; pour des classes nombreuses, utiliser un SFU (LiveKit/Jitsi/mediasoup/Janus). La signalisation WebSocket ne change pas cette limite média.
2. **Signaux sortants live** : l’envoi métier reste validé par POST HTTP avant diffusion WebSocket. C’est robuste et simple à auditer, mais une très forte fréquence de collaboration peut justifier un canal bidirectionnel spécialisé.
3. **TURN** : indispensable en production sur certains NAT/réseaux mobiles ; tester les credentials temporaires et le routage UDP/TCP/TLS depuis plusieurs opérateurs.
4. **CSP style** : `style-src 'unsafe-inline'` reste nécessaire aux styles calculés/Tailwind actuels. Le risque script est isolé, mais supprimer cette exception CSS demanderait une refonte de certains composants/styles.
5. **Stockage Railway** : activer S3/R2/Backblaze/etc. et `REQUIRE_REMOTE_MEDIA=True`; le disque Railway ne doit pas être la source durable.
6. **Antivirus/CDR** : ClamAV est intégré ; une CDR dédiée peut être ajoutée si le partage documentaire devient ouvert à très grande échelle.
7. **Exécution framework** : aucun runner serveur arbitraire n’est fourni volontairement. Pour exécuter Django/Node/Java/C++, déployer un service sandbox éphémère dédié (conteneurs isolés, quotas CPU/RAM/temps, aucun secret/réseau interne).
8. **Clés et webhooks live** : doivent être créés dans les comptes Stripe/GeniusPay/YouCan Pay/CinetPay et testés sur les environnements réels ; le code ne peut pas valider des credentials inexistants.
9. **Release gates** : le build Next.js, Playwright et les tests Django complets doivent être verts en CI avant déploiement ; ils ne sont pas certifiés par l’analyse statique seule.

## Checklist Railway / Vercel

- [ ] `DEBUG=False`, SECRET_KEY forte, `ALLOWED_HOSTS` exact.
- [ ] HTTPS et paramètres HSTS choisis explicitement.
- [ ] PostgreSQL + Redis Railway configurés.
- [ ] S3-compatible actif, médias persistants testés.
- [ ] SMTP testé depuis l’outil Admin.
- [ ] Passerelles sandbox testées depuis l’outil Admin puis clés live configurées.
- [ ] Webhooks Stripe/GeniusPay enregistrés sur l’URL Railway HTTPS.
- [ ] `API_PROXY_TARGET` Vercel pointe vers le backend Railway et le navigateur utilise `/api` same-origin.
- [ ] `NEXT_PUBLIC_WS_URL=wss://<backend-railway>/ws` configuré sur Vercel si `/ws` n’est pas reverse-proxyé par le domaine frontend.
- [ ] `CORS_ALLOWED_ORIGINS` et `REALTIME_ALLOWED_ORIGINS` contiennent seulement les domaines Vercel/personnalisés attendus.
- [ ] TURN configuré côté backend (`RTC_TURN_URL` + idéalement `RTC_TURN_SECRET`) et testé depuis 4G/5G et réseaux d’entreprise.
- [ ] Tests Django, `npm run test:security`, build Next.js, Playwright et `docker compose config` réussis dans CI/l’environnement de livraison.
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

## Validation v46 — Projets & portfolio

- Compilation Python du backend : OK.
- Analyse syntaxique TypeScript/TSX : 114 fichiers, 0 erreur.
- `docker-compose.yml` : YAML valide.
- `package.json` et `tsconfig.json` : JSON valides.
- Préfixes de migrations : aucun doublon détecté.
- Invariants vérifiés : `apps.projects` installé, routes `/api/projects/` présentes, migration `projects.0001_initial` présente, blocage Nginx des artefacts de remise privés présent.
- Django n'étant pas installé dans l'environnement d'audit, `manage.py check`, les tests Django et le build Next.js complet doivent être exécutés dans les conteneurs du projet avant mise en production.


## Validation v53 — Navigation, domaines et performance

- Navigation desktop : menus hover/focus pour Formations, Mentorat et Opportunités ; version mobile repliable.
- Taxonomie Domain : migration `catalog.0006_domain_category_domain`, endpoint public et filtres Cours/PDF/Cohortes.
- Performance backend : suppression des N+1 principaux sur catalogue, cohortes et mentorat ; serializers de liste compacts et annotations SQL.
- Performance frontend : cache serveur court des données publiques, image hero WebP d’environ 44 Ko, Turbopack en développement et réutilisation du volume `node_modules`.
- Compilation syntaxique Python : OK.
- Parsing/transpilation des fichiers TS/TSX modifiés : OK.
- YAML/JSON : OK.
- Audit mobile : OK, aucune alerte bloquante.
- Tests statiques de sécurité frontend : 4/4 OK.
- `manage.py test`, build Next.js complet et Playwright restent des release gates à exécuter dans Docker/CI.


## Audit v80 — Paiements / Mobile Money

Le code financier dispose désormais d’un historique persistant de tentative/événement/anomalie et ne dépend plus d’un cache éphémère pour l’idempotence webhook. Le fulfillment est bloqué si la référence, le montant ou la devise ne concordent pas avec la commande. Les commandes externes anciennes sont signalées pour revue sans être automatiquement invalidées, afin de préserver les confirmations Mobile Money tardives. La validation live des prestataires reste conditionnée à la configuration des comptes marchands réels.
