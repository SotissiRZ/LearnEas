# v57 — Salle live adaptative & planning modifiable

- Mode vidéo **Auto** : lorsque l'utilisateur est seul, la scène d'attente reste principale et sa caméra devient une petite vignette en bas à droite.
- Passage automatique en galerie lorsque des participants distants arrivent.
- Partage d'écran prioritaire en mode focus avec caméra du présentateur en PiP.
- Sélecteur manuel `Auto / Galerie / Intervenant` dans la salle live.
- Les vignettes compactes n'étirent plus la colonne vidéo sur toute la hauteur de la scène.
- Le planning instructeur permet désormais de modifier inline la date, l'heure et la durée de chaque séance future.
- Durée de séance configurable entre 15 et 480 minutes ; les séances déjà démarrées/terminées sont verrouillées.
- Les dates publiques de la cohorte (`start_date` / `end_date`) se synchronisent avec le planning réel après création, modification ou suppression d'une séance.
- Tests backend ajoutés pour modification autorisée, refus apprenant et verrouillage après démarrage.
- Documentation : `docs/LIVE_PLANNING_V57.md`.

# v56 — Modèle économique & page Tarifs

- Nouvelle page publique `/pricing` avec une grille distincte pour apprenants, instructeurs, mentors et entreprises/recruteurs.
- Ajout de `Tarifs` dans la navbar desktop/mobile et dans le footer.
- Modèle de lancement : apprenant pay-as-you-go sans abonnement obligatoire, commission marketplace pour créateurs/mentors et forfaits B2B recrutement.
- Paramètres commerciaux administrables depuis le back-office : Pro instructeur, commission Pro, commission mentor, annonce recruteur à l'unité, Pro/Business et quotas d'offres.
- Les montants commerciaux restent stockés en EUR et sont convertis par le sélecteur de devise existant (XOF/XAF compris lorsqu'ils sont actifs).
- La commission mentor devient indépendante et est réellement utilisée lors du split de revenus au checkout.
- Les offres Pro/Business sont explicitement présentées comme offres commerciales sur demande tant que la facturation récurrente automatique n'est pas branchée.
- Migration : `accounts.0008_pricing_model`.
- Documentation : `docs/PRICING_BUSINESS_MODEL.md`.

# v55 — Menus navbar auto-repliables

- Les menus déroulants desktop sont désormais contrôlés par état React.
- Ouverture au survol et au focus clavier.
- Fermeture automatique lorsque le curseur quitte la zone complète du menu.
- Fermeture immédiate lorsqu’un lien du panneau est sélectionné.
- Fermeture au clic extérieur et avec la touche Échap.
- Suppression du comportement `focus-within` qui pouvait laisser un menu affiché après navigation.

# v54 — Navbar élargie et hero visuel corrigé

- Navbar desktop portée à un conteneur dédié jusqu’à 1680 px afin de conserver les libellés, la recherche, la devise, le panier et les actions d’authentification sur une seule ligne.
- Les libellés desktop sont `whitespace-nowrap`; le menu mobile prend le relais avant que la navigation ne devienne trop dense.
- Hauteur de navigation portée à 80 px et espace de layout synchronisé.
- Hero de l’accueil restructuré en deux vraies colonnes : contenu à gauche, image KalanPro visible à droite.
- Nouvelle image hero légère (`hero-kalanpro.webp`, ~39 Ko) avec affichage responsive y compris sur mobile.
- Suppression de l’ancien fond hero recadré qui rendait l’illustration presque invisible.

# v52 — KalanPro branding & interface

- Renommage public de la plateforme en KalanPro.
- Nouvelle palette navy + orange appliquée via Tailwind.
- Refonte complète de la page d’accueil.
- Nouvelle navigation, footer, page À propos et écrans d’authentification.
- Sidebars instructeur/admin harmonisées.
- Migration des paramètres et comptes de démonstration existants.
- Correctifs Docker dev conservés pour un démarrage local plus robuste.

# v51 — Realtime WebSocket, TURN éphémère, CSP stricte et tests E2E

- Backend basculé en ASGI/Daphne avec Django Channels + `channels-redis`; Redis devient aussi le bus realtime des salles live.
- Signalisation entrante, présence, fichiers et états de séance poussés par WebSocket avec ticket signé court et contrôle d’origine.
- Suppression du poll permanent à 1 seconde ; heartbeat à 15 s et fallback HTTP à 3 s uniquement lorsque le WebSocket est indisponible, avec reconnexion exponentielle.
- Conservation du POST HTTP pour les signaux sortants afin de réutiliser les validations DRF et la modération métier avant diffusion realtime.
- Credentials ICE/TURN déplacés côté backend : génération temporaire compatible secret partagé coturn (`RTC_TURN_SECRET`) et suppression des secrets `NEXT_PUBLIC_RTC_*`.
- CSP principale Next.js générée par requête avec nonce + `strict-dynamic`; aucun `script-src unsafe-inline` ni `unsafe-eval` en production. `unsafe-eval` n’est ajouté que sous `NODE_ENV=development` pour le tooling Next local.
- Mini-runner JavaScript/Python déplacé sous `/code-runner/`, chargé dans une iframe `sandbox="allow-scripts"` sans `allow-same-origin`, puis exécuté dans des Workers avec timeout. Pyodide/CDN/wasm restent confinés à la CSP du runner.
- Aperçus HTML/CSS rendus dans des iframes sans permission de script.
- Nginx reverse-proxy `/ws/` ajouté ; Docker dev utilise `ws://localhost:8000/ws`. Le `X-Frame-Options: DENY` global Nginx est retiré afin de ne pas bloquer le runner same-origin ; les routes sensibles conservent leurs headers explicites.
- Tests backend ajoutés pour ticket realtime, push Channels et credentials TURN temporaires.
- `npm run test:security` ajoute quatre garde-fous statiques auth/CSP/realtime/runner.
- Smoke tests Playwright ajoutés et exécutés par la CI après le build Next.js.
- Documentation Railway/Vercel/RTC mise à jour ; correction d’une variable AWS dupliquée dans Compose.

# v50 — Sécurité auth, SQL, uploads et files Celery

- Refresh JWT déplacé dans un cookie HttpOnly ; access token uniquement en mémoire et durée ramenée à 15 minutes.
- Proxy `/api` configurable côté Vercel pour conserver une origine navigateur unique avec Railway.
- Contrôle Origin sur refresh/logout, refresh HttpOnly stable multi-onglets, et révocation lors du logout/changement de mot de passe.
- Suppression des N+1 du matching opportunités et des listes de projets apprenant.
- Revalidation administrateur obligatoire après modification de l'identité d'une entreprise approuvée.
- Validation des signatures PDF/Office/ZIP/VTT et protections ZIP traversal/zip-bomb.
- Client ClamAV INSTREAM intégré ; scan documentaire requis par défaut lorsque `DEBUG=False`.
- Durée des liens privés classiques ramenée à 15 minutes ; fenêtre HLS séparée à 6 heures.
- Files Celery `media`, `notifications`, `default` et worker média Docker séparé.
- Tests de régression ajoutés pour cookie HttpOnly, rotation/logout, origine inconnue, entreprise revalidée et faux fichiers.

# v48 — Emplois, missions & matching professionnel

- Nouveau module `apps.opportunities` : entreprises, profils candidats, opportunités et candidatures.
- Marketplace publique `/opportunities` : emplois, stages, freelance et missions avec filtres pays/type/mode/niveau.
- Matching candidat explicable 0–100 basé sur compétences du profil, portfolio, certificats actifs, métier recherché, expérience et préférences de pays/mode/type.
- Profil candidat avec CV privé, pays choisis dans le référentiel KalanPro et visibilité recruteur opt-in ; sélection multi-pays adaptée mobile (liste + recherche, sans saisie libre).
- Candidatures KalanPro avec snapshot immuable des compétences, certificats actifs, projets vérifiés et copie du CV effectivement transmis au moment de la candidature.
- Espace recruteur : validation entreprise, publication, pipeline de candidatures et vivier de talents.
- Back-office : nouvel onglet Recrutement pour approuver/refuser/suspendre les entreprises et contrôler les annonces.
- Confidentialité : les CV ne sont plus accessibles directement sous `/media/`; la rémunération masquée n'est pas exposée publiquement ; les candidatures retirées ne peuvent pas être réactivées par un recruteur.
- Seed démo : Demo Digital Africa, deux opportunités, un recruteur et une candidature Fatou.
- Nouvelle migration : `opportunities/0001_initial.py`.

# v47 — Certificats vérifiables, QR et registre immuable

- Chaque certificat dispose désormais d’un **QR code public** pointant vers le registre KalanPro.
- La page de vérification accepte le **numéro de certificat ou le code UUID**, et affiche explicitement Valide / Révoqué / Expiré.
- Snapshot serveur des preuves au moment de l’émission : émetteur, compétences et projets pratiques approuvés avec note, barème, validateur et date.
- Ajout d’une **empreinte SHA-256** du snapshot public pour détecter les altérations de données.
- Réémission rendue historique : un nouveau certificat est créé au lieu d’écraser l’ancien numéro/QR ; l’ancien registre reste consultable et référence son remplacement.
- Nouveau journal `CertificateEvent` pour tracer émission, révocation, expiration et réémission ; Celery Beat matérialise les expirations chaque heure.
- La révocation exige maintenant un motif et n’efface jamais le certificat.
- Les certificats v46 existants sont conservés et enrichis par la migration ; ils restent vérifiables.
- Ajout de `qrcode==8.2` au backend.
- Documentation : `docs/CERTIFICATES_VERIFIABLES.md`.
- **Migration requise :** `enrollments.0005_verifiable_credentials`.

---

# v46 — Projets pratiques + portfolio professionnel

- Nouvelle application `apps.projects` pour transformer les cours en preuves de compétence : briefs, objectifs, livrables, compétences, échéances, barèmes et ordre d’affichage.
- Les instructeurs peuvent rendre un projet facultatif ou **obligatoire pour le certificat**, définir la note minimale et encadrer les nouvelles remises.
- Remises apprenant avec résumé, URL de démonstration, dépôt Git, fichier privé, couverture et compétences ; chaque remise formelle conserve une **révision immuable**.
- Workflow de correction : remis → approuvé / modifications demandées / rejeté, avec note et feedback instructeur.
- Le certificat exige désormais la progression pédagogique **et** l’approbation de tous les projets obligatoires publiés ; les certificats déjà émis ne sont jamais invalidés rétroactivement.
- Nouveau **portfolio professionnel** apprenant : slug public, bio, compétences, liens professionnels, statut ouvert aux opportunités et contrôles de confidentialité.
- Publication d’un projet approuvé avec badge **Vérifié par KalanPro** et snapshot serveur immuable du cours, du projet, de l’instructeur, de la date, de la note et du barème.
- Ajout possible de réalisations externes non vérifiées afin que le portfolio puisse également représenter le travail réalisé hors KalanPro.
- Page publique `/portfolio/<slug>` sans email ni téléphone ; le pays et les notes ne sont affichés que si l’apprenant l’autorise.
- Les fichiers de projet restent privés via les médias protégés/signés ; Nginx bloque l’accès direct aux remises et aux révisions.
- Nouveaux espaces : `Mes projets`, `Mon portfolio`, `Projets & corrections`, ainsi qu’un onglet Projet dans le lecteur de cours.
- Le catalogue de cours indique le nombre de projets pratiques et ceux requis pour la certification.
- `seed_demo` prépare un projet approuvé et un portfolio public pour le compte Fatou afin de tester immédiatement le parcours.
- Documentation : `docs/PROJECTS_PORTFOLIO.md`.
- **Migration requise :** `projects.0001_initial`.

---

# v45 — Cohortes live + mentorat 1:1

- Transformation des formations live en **cohortes** avec nom de cohorte, fuseau IANA, minimum/maximum de participants et date limite d'inscription.
- Fermeture automatique des inscriptions après la date limite, au démarrage de la cohorte ou lorsque les places sont épuisées ; les réservations de dernière place restent transactionnelles au checkout.
- Export `.ics` du planning d'une cohorte pour l'ajouter à un calendrier externe.
- Nouvelle marketplace publique **Mentorat 1:1** : offres publiables par les instructeurs, durée, tarif, langue, fuseau et politique de réservation/annulation.
- Gestion des créneaux avec verrou transactionnel/contrainte SQL empêchant deux réservations actives du même rendez-vous.
- Checkout payant du mentorat intégré au moteur KalanPro existant (EUR comptable, conversion/devise locale, CinetPay/Stripe/etc.) avec snapshot financier et commission plateforme.
- Une réservation payante conserve le créneau 45 min avant checkout puis jusqu'à 2 h après création de la commande pour absorber les confirmations Mobile Money différées.
- Création automatique d'une **salle vidéo KalanPro privée** par créneau ; l'apprenant confirmé n'obtient accès qu'à sa séance. Les conteneurs techniques sont exclus du catalogue et des certificats.
- Espace apprenant pour suivre, payer, rejoindre ou annuler ses rendez-vous ; espace instructeur pour créer des offres, publier des créneaux, ouvrir la salle et clôturer la séance avec une note de suivi.
- Application du délai minimum d'annulation côté apprenant ; aucun remboursement silencieux n'est déclenché par une simple annulation de rendez-vous.
- Rappels WhatsApp v44 étendus aux rendez-vous de mentorat, pour l'apprenant et le mentor lorsque chacun a opté pour le canal.
- Redirection de retour de paiement vers l'espace mentorat pour une commande composée uniquement de mentorat.
- **Pays sans saisie libre** : inscription, profils apprenant/instructeur et paramètres légaux utilisent désormais un référentiel pays/territoires, avec les marchés d'Afrique francophone placés en tête.
- **Téléphones sans indicatif saisi manuellement** : WhatsApp et retraits Mobile Money proposent un sélecteur pays/indicatif puis un champ pour le numéro national ; KalanPro reconstruit et valide le format E.164 côté serveur.
- Les valeurs pays sont normalisées/validées côté API afin qu'un client ne puisse pas contourner les listes de l'interface.
- Sécurisation du cycle mentorat/paiement : une commande externe encore en attente conserve le verrou du créneau, une commande définitivement échouée le libère, et une confirmation payée tardive ne perd pas silencieusement la réservation.
- Les offres/créneaux ayant un historique de réservation ne peuvent plus être supprimés physiquement : ils doivent être dépubliés/désactivés afin de conserver la traçabilité financière et pédagogique.
- Documentation : `docs/MENTORSHIP.md`.
- **Migrations requises :** `formations.0009_cohorts_and_mentorship` et `payments.0011_mentorship_order_items`.

---

# v44 — WhatsApp transactionnel et relances automatiques

- Intégration directe de Meta WhatsApp Cloud API avec version Graph API configurable.
- Consentement explicite et numéro E.164 dans les profils apprenant/instructeur.
- Préférences séparées : paiements, rappels live, inactivité et certificats.
- Notifications idempotentes après paiement confirmé et émission/réémission de certificat.
- Rappel automatique avant les formations live via Celery Beat.
- Relance hebdomadaire maximum des cours inactifs, après délai administrable.
- Webhook Meta signé : suivi envoyé/livré/lu/échec.
- Mode local `WHATSAPP_DRY_RUN=True` : workflow testable sans compte Meta ni message réel.
- Paramètres administrateur pour activer le canal, les templates et les délais.
- Nouveau service Docker `celery_beat`.
- Documentation : `docs/WHATSAPP.md`.

# v43 — HLS adaptatif + mode faible connexion / audio-only

- Génération asynchrone via **Celery + ffmpeg** d'un paquet HLS multi-bitrate pour chaque vidéo uploadée.
- Profils orientés réseaux mobiles : **240p, 360p, 480p et 720p**, sans upscale au-delà de la source.
- Génération d'une piste **audio-only ~48 kb/s** pour suivre un cours avec une consommation de données minimale.
- Le lecteur utilise **hls.js** sur Chrome/Firefox/Edge/Android et le HLS natif lorsque le navigateur le prend en charge.
- Nouveau réglage **Économie de données** : le mode Auto est plafonné à 360p et le choix est mémorisé dans le navigateur ; activation automatique si `Save-Data`/2G est détecté.
- Sélecteur de qualité Auto / 240p / 360p / 480p / 720p et bascule Audio uniquement, avec conservation du timestamp lors du changement de source.
- Les manifests HLS restent privés : chaque playlist/segment est servi par une URL signée expirante et les manifests sont réécrits côté Django ; aucun répertoire HLS n'est exposé publiquement.
- Support local via `X-Accel-Redirect` et stockage S3-compatible via URL présignée.
- Régénération HLS disponible côté instructeur/admin, statut visible dans l'éditeur de cours, et nettoyage des anciens paquets lors d'une régénération ou suppression de leçon.
- Commande de migration des anciennes vidéos : `python manage.py prepare_course_streaming`.
- Correction d'une déclaration `const video` dupliquée dans le lecteur vidéo qui pouvait casser la compilation TypeScript.
- Ajout de `hls.js` 1.6.13 au frontend.
- **Migration requise :** `catalog.0005_lesson_adaptive_streaming`.

---

# v42 — Mobile Money Afrique francophone (CinetPay)

- Ajout d’un vrai driver **CinetPay Mobile Money** au moteur de paiement KalanPro, sans exposer les secrets au frontend.
- Prise en charge initiale de **XOF** et **XAF**, activées avec le taux CFA fixe de **655,957 pour 1 EUR** et zéro décimale.
- Les comptes dont le pays est Sénégal/Côte d’Ivoire/Mali/Burkina Faso/Bénin/Togo/Niger privilégient automatiquement XOF lors de la première visite ; Cameroun/Congo/Gabon/Tchad/RCA privilégient XAF. Le choix manuel de devise reste prioritaire et mémorisé.
- Checkout CinetPay limité au canal `MOBILE_MONEY`, avec redirection vers le guichet sécurisé CinetPay et affichage du montant réellement facturé.
- Normalisation automatique des montants CinetPay au multiple de 5 exigé par le prestataire, enregistrée dans la commande avant initialisation du paiement.
- Webhook CinetPay sécurisé par **X-TOKEN HMAC SHA-256** puis vérification serveur via `/payment/check` avant toute délivrance de cours/PDF/formation.
- Le webhook est idempotent et ne marque pas prématurément comme échoués les états d’attente opérateur.
- Ajout d’une page de retour de paiement KalanPro qui vérifie la commande et attend la confirmation opérateur/webhook avant d’accorder l’accès.
- Ajout des variables `CINETPAY_*` et `BACKEND_PUBLIC_URL` pour Railway/Vercel et les environnements locaux.
- L’admin peut ajouter/activer CinetPay et définir ses devises. Le preset démarre en live désactivé/XOF ; les variables sandbox restent prévues pour un futur environnement de test CinetPay.
- **Migration requise :** `payments.0010_cinetpay_mobile_money`.

---

# v41 — Vignette présentateur déplaçable pendant le partage d’écran

- Le partage d’écran ne remplace plus visuellement le présentateur : KalanPro fabrique un **flux composite écran + caméra** envoyé aux autres participants.
- La caméra du présentateur apparaît en **petite vignette Picture-in-Picture** au-dessus de la présentation.
- La vignette est **déplaçable par glisser-déposer** ; sa position est intégrée au flux partagé et donc visible au même endroit pour les autres participants.
- Le présentateur conserve localement une prévisualisation nette de l’écran, avec une vignette DOM indépendante afin que le déplacement reste fluide.
- Si la caméra est coupée pendant la présentation, la vignette reste présente avec l’avatar/initiale ; elle reprend automatiquement la vidéo lorsque la caméra est rallumée.
- Le bouton caméra reste utilisable pendant le partage d’écran : il masque/affiche la caméra du présentateur sans interrompre la présentation.
- Le flux composite est produit en canvas jusqu’à **1280×720 à 30 i/s** pour limiter la charge CPU et rester compatible avec la piste WebRTC déjà négociée.
- À l’arrêt du partage, la piste composite est libérée et la caméra classique est restaurée sur le sender WebRTC existant, sans second sender vidéo.
- Nettoyage renforcé des pistes/canvas/animations lors d’une sortie de salle, d’une coupure de partage ou d’un échec de capture.
- Aucune migration de base de données n’est requise.

---

# v40 — Extinction réelle de la caméra en réunion

- Le bouton **Caméra** ne se contente plus de désactiver `track.enabled` : la piste vidéo est retirée du `MediaStream`, détachée des pairs WebRTC puis arrêtée avec `MediaStreamTrack.stop()`.
- La caméra matérielle est donc réellement libérée lorsque l’utilisateur la coupe ; l’indicateur caméra du navigateur/OS peut s’éteindre immédiatement.
- Rallumer la caméra recrée une nouvelle piste via `getUserMedia()` puis la rattache au sender WebRTC existant.
- Correction de `replaceTrackOnPeers()` pour retrouver un sender vidéo même après `replaceTrack(null)`, évitant la création de senders vidéo en double lors d’un OFF → ON.
- La commande organisateur **Couper caméra** applique la même libération matérielle, y compris pendant un partage d’écran sans interrompre le partage.
- Changer de périphérique caméra lorsque la caméra est coupée ne déclenche plus `getUserMedia()` : le choix est mémorisé et appliqué au prochain allumage.
- Le sélecteur de caméra est verrouillé pendant le partage d’écran afin d’éviter des transitions de flux concurrentes.
- Aucune migration de base de données n’est requise.

---

# v39 — Lecteur vidéo proportionnel + navbar fixe

- Navbar principale conservée fixe en haut de l’écran.
- En-tête du workspace de cours reste positionné sous la navbar fixe.
- Retour au lecteur vidéo 16:9 pleine largeur de v37 : suppression de la hauteur forcée de v38.
- Suppression du conteneur desktop qui déformait visuellement l’espace vidéo.
- Le flux vidéo est désormais affiché intégralement avec son ratio naturel, sans recadrage ni agrandissement artificiel.
- Fond de l’en-tête du workspace rendu opaque pour éviter le texte pâle/invisible.

# v38 — Navbar fixe et viewport de lecture plus compact

- La navbar principale est désormais **fixée en haut de l’écran** sur toute la plateforme, avec un espace de compensation de 64 px afin qu’aucun contenu ne passe dessous.
- L’en-tête du workspace de cours reste collé juste sous la navbar pendant le défilement.
- Sur desktop, la zone vidéo est plafonnée à une hauteur responsive (`clamp(430px, 58vh, 650px)`) au lieu d’occuper toute la largeur en ratio 16:9.
- Cette hauteur plus compacte laisse apparaître dès l’ouverture les contrôles de navigation et un aperçu du titre/onglets pédagogiques situés sous la vidéo, tout en conservant le ratio natif sur mobile.
- Le lecteur conserve ses fonctions v37 et la politique vidéo non téléchargeable de v36.
- Aucune migration de base de données n’est requise.

---

# v37 — Expérience de lecture type plateforme premium

- Refonte complète de l'espace de lecture des cours avec une ergonomie inspirée des grandes plateformes de formation : **sommaire repliable**, espace vidéo sombre, navigation précédent/suivant et zone pédagogique à onglets.
- Le lecteur vidéo conserve l'interdiction de téléchargement et adopte des contrôles plus discrets : timeline superposée, ±10 s, volume, vitesse 0,5×–2×, sous-titres, Picture-in-Picture, plein écran et raccourcis clavier.
- Ajout de la **lecture automatique de la leçon suivante**, mémorisée par utilisateur dans le navigateur.
- Ajout de la **reprise de lecture** : la dernière leçon et la position précise sont persistées côté backend et restaurées à la prochaine ouverture.
- Ajout d'un **carnet personnel horodaté** : création, modification, suppression, retour au timestamp et export texte des notes. Les notes sont privées et isolées par utilisateur.
- Refonte de la **transcription** avec recherche dans la vidéo ou dans tout le cours. Les lignes au format `[mm:ss]` / `[hh:mm:ss]` deviennent cliquables et déplacent le lecteur au passage concerné.
- L'onglet **Q&R** utilise maintenant le vrai système de commentaires de leçon : questions apprenant et réponses instructeur sont visibles directement sous le lecteur.
- Les ressources PDF restent disponibles dans un onglet dédié et ne modifient pas la politique de non-téléchargement des vidéos.
- Ajout de tests backend pour la confidentialité du carnet et la persistance de la position de lecture.
- **Migration requise** : `0004_lessonnote` ajoute le carnet personnel et `last_position_seconds` au suivi de leçon.

---

# v36 — Protection contre le téléchargement vidéo

- Suppression des boutons de téléchargement/ouverture directe du lecteur vidéo.
- Ajout de `controlsList="nodownload noremoteplayback"`, désactivation du clic droit et du glisser-déposer sur les vidéos.
- Les médias vidéo privés sont servis en `inline`, `private, no-store` et l'ouverture directe de type document/iframe est refusée côté backend.
- Les PDF ne sont pas concernés par ces restrictions vidéo.

---

# v35 — Sélecteur de devise global dans la navbar

- Ajout d'un **sélecteur de devise global** dans la barre de navigation, disponible sur desktop et dans le menu mobile.
- La sélection est alimentée par les devises actives configurées dans **Admin → Paramètres → Paiements & devises** ; aucune liste de devises n'est codée en dur côté interface.
- La préférence est conservée dans le navigateur (`localStorage` + cookie) et revient automatiquement lors des visites suivantes.
- Tous les prix catalogue (cours, PDF, formations), le panier, le checkout et les montants de synthèse des dashboards sont convertis instantanément depuis la base comptable **EUR** avec le taux administré.
- Le checkout reprend automatiquement la devise choisie dans la navbar ; changer la devise au checkout synchronise aussi la navbar et filtre les moyens de paiement compatibles.
- Les commandes historiques restent affichées dans **leur devise réellement facturée** (`total_amount` + `currency`) afin de ne pas reconvertir un montant déjà payé.
- Les formulaires de création de prix, commissions et demandes de retrait restent volontairement libellés en **EUR**, qui demeure l'unité comptable de référence.
- Aucun changement de schéma de base de données : **aucune migration supplémentaire** n'est requise pour v35.

---

# v34 — Euro comme devise comptable de base

- La devise comptable de base de KalanPro passe de **MAD à EUR** : prix catalogue, revenus instructeurs, commissions, retraits et total de base sont désormais exprimés en euros.
- **EUR est forcé actif avec un taux égal à 1** et devient la devise de checkout par défaut après migration. MAD reste disponible comme devise secondaire et son taux devient le nombre de MAD pour 1 EUR.
- Migration de données prudente : les montants existants en MAD sont convertis en EUR avec le taux EUR/MAD déjà configuré dans la table des devises, afin d'éviter de transformer par erreur un prix de 300 MAD en 300 EUR. Les montants réellement facturés des commandes historiques (`total_amount` + `currency`) restent inchangés.
- Tous les autres taux sont automatiquement rebasés de « devise par 1 MAD » vers « devise par 1 EUR ».
- Interface, checkout, formulaires instructeur, revenus et seuil de retrait affichent désormais l'euro comme unité comptable.
- Le seuil de retrait par défaut passe de 100 MAD à **10 EUR** pour les nouvelles configurations.
- Les données de démonstration ont été réétalonnées en EUR avec une valeur proche de leur ancien équivalent en MAD.

---

# v33 — Compatibilité vidéo réelle et réparation automatique

- Correction de l'erreur navigateur **MEDIA_ERR_SRC_NOT_SUPPORTED / Source vidéo non prise en charge** sur les fichiers MP4/MOV techniquement valides mais encodés avec un codec non universel (HEVC/H.265, H.264 10-bit, audio incompatible, etc.).
- Les nouveaux uploads vidéo sont inspectés avec `ffprobe` puis, seulement si nécessaire, convertis automatiquement par `ffmpeg` vers **MP4 H.264/AAC yuv420p + faststart**, format compatible avec les navigateurs desktop et mobiles.
- Ajout d'une réparation asynchrone des anciennes vidéos via Celery : un administrateur ou l'instructeur propriétaire voit désormais **Réparer cette vidéo** directement dans le lecteur lorsqu'une vidéo uploadée échoue.
- Ajout des endpoints `repair-video` / `repair-video-status` et d'un suivi de conversion côté lecteur sans bloquer Gunicorn.
- Ajout de la commande `python manage.py normalize_course_videos` pour auditer/réparer en masse les vidéos déjà stockées.
- Correction de `X-Accel-Redirect` pour les noms de fichiers contenant espaces/accents : l'URI interne nginx est maintenant percent-encodée.
- Timeouts d'upload/transcodage alignés à 3600 s pour les vidéos longues.
- Variables `VIDEO_NORMALIZATION_ENABLED`, `VIDEO_PROBE_TIMEOUT_SECONDS`, `VIDEO_TRANSCODE_TIMEOUT_SECONDS`, `VIDEO_TRANSCODE_PRESET` et `VIDEO_TRANSCODE_CRF` documentées.

---

# v32 — Correctif lecteur vidéo et streaming

- Correction du lecteur vidéo HTML5 : vrais contrôles Lecture/Pause, seek, durée, volume, vitesse, boucle, Picture-in-Picture, plein écran, raccourcis clavier, état de chargement et message d'erreur exploitable.
- Les URLs vidéo externes HTTPS ne sont plus bloquées par la CSP Nginx ; les liens YouTube et Vimeo déjà présents sont rendus dans leurs lecteurs intégrés.
- Les URLs privées `/api/media/private/` sont résolues vers l'origine publique du backend lorsque frontend et API sont déployés sur deux domaines différents (cas Vercel + Railway).
- Streaming privé durci : `Accept-Ranges: bytes`, buffering proxy désactivé et `proxy_force_ranges` afin de permettre chargement des métadonnées, lecture et déplacement dans une vidéo.
- Quota média rendu configurable par `MEDIA_THROTTLE_RATE` et relevé en développement pour éviter les 429 provoqués par les requêtes Range d'un lecteur vidéo.
- Ajout d'un test de régression vérifiant MIME vidéo, `Accept-Ranges`, `X-Accel-Buffering` et `X-Accel-Redirect`.

---

# v31 — Lecteurs, paiement test, panier et contrôle admin

- Correction du lecteur PDF privé : le backend renvoie désormais le vrai `Content-Type` (`application/pdf`) et un `Content-Disposition: inline`, ce qui empêche l'affichage des octets PDF sous forme de texte illisible (`%PDF`, `endstream`, caractères corrompus).
- Les leçons marquées **Aperçu gratuit** sont maintenant réellement cliquables depuis la fiche du cours et s'ouvrent dans un lecteur vidéo intégré.
- Le programme du cours est réhydraté avec la session JWT : un administrateur voit et peut lire toutes les leçons et ressources PDF, même verrouillées pour le public.
- Ajout d'un espace de **vérification administrateur** dédié pour les cours, PDF et formations, y compris les contenus non publiés.
- Refonte visuelle de l'onglet admin **Contenus** : cartes éditoriales, états, indicateurs, accès de vérification, fiche publique, publication, mise en avant et suppression.
- Ajout d'un **paiement test KalanPro** local : simulation d'un paiement réussi sans carte ni API externe lorsque `TEST_PAYMENTS_ENABLED=True`. Le mode est désactivable et doit rester désactivé en production.
- Le panier est vidé immédiatement à la déconnexion pour éviter qu'un nouveau compte retrouve les articles du compte précédent.
- Tests de régression ajoutés pour le MIME PDF, l'accès admin complet et le paiement test.

---

# v30 — Correctif 429 / healthcheck frontend

- Correction de la cause des `429 Too Many Requests` observés sur les endpoints catalogue : le healthcheck Docker du frontend sondait `/` toutes les 15 secondes, ce qui exécutait la page d'accueil Next.js côté serveur et déclenchait trois appels API (`categories`, `featured`, `pdfs`) à chaque sonde.
- Ajout d'un endpoint frontend dédié et sans dépendance backend, `GET /healthz`, puis bascule du healthcheck Docker vers cet endpoint léger.
- Throttling global DRF rendu configurable par `ANON_THROTTLE_RATE` et `USER_THROTTLE_RATE`, avec des valeurs de développement suffisamment hautes pour les tests locaux tout en conservant des valeurs de production bornées par défaut.
- Les quotas sensibles existants (`auth`, `password_reset`, `checkout`, `media`, `live`, `admin_test`, `webhook`) restent inchangés.
- Le frontend distingue désormais un HTTP 429 d'une panne réseau : le bandeau indique un chargement temporairement limité au lieu de prétendre que le serveur est injoignable.
- Documentation des variables de throttling dans les exemples d'environnement Docker/backend.

---

# v29 — Upload vidéo volumineux & lecteur PDF débloqué

- Correction de l'erreur HTTP **413** lors de l'ajout de vidéos de cours : limite Nginx portée à 2 Go, timeouts d'upload/proxy étendus et timeout Gunicorn adapté aux traitements longs.
- Limites médias backend rendues configurables (`MAX_VIDEO_UPLOAD_MB`, `MAX_PDF_UPLOAD_MB`, `MAX_IMAGE_UPLOAD_MB`) avec bascule rapide des gros fichiers vers le stockage temporaire disque.
- Validation frontend des formats et tailles vidéo avant l'envoi, avec message d'erreur 413 explicite et progression conservée.
- Formats vidéo explicitement supportés : MP4, WebM, MOV et M4V.
- Correction du lecteur PDF bloqué par la CSP Nginx : `frame-src` autorise désormais les ressources KalanPro de même origine et les blobs, sans rendre le site lui-même intégrable par un tiers.
- Le point d'accès média signé est exempté de `X-Frame-Options: DENY` uniquement pour les médias privés, avec `frame-ancestors` limité aux frontends configurés.
- Les médias privés servis localement utilisent `SAMEORIGIN`, `Accept-Ranges` et restent `private, no-store` afin de préserver lecture, recherche, zoom et navigation native des PDF/vidéos.
- Durée de validité des URLs médias signées rendue configurable et portée à 12 h par défaut pour éviter les coupures lors de longues sessions d'apprentissage.
- Tests de régression ajoutés pour la limite vidéo configurable et l'intégration du lecteur PDF signé.

---

# v28 — Audit complet, mini-IDE multi-fichiers & paiements configurables

### Finitions de livraison
- Checkout gratuit : acquisition possible même si aucune passerelle externe n’est active/configurée.
- IDE multi-fichiers : chemins normalisés et uniques ; correction d’un identifiant manquant détecté au contrôle TypeScript.
- PostgreSQL/Django : contrainte de réservation raccourcie à `uniq_order_form_res` et migration `payments/0008` de compatibilité pour les bases v27 déjà migrées.
- Diagnostic email : validation Django réelle de l’adresse destinataire.
- Rapport d’audit final : séparation explicite entre contrôles statiques réussis et contrôles runtime qui devront être rejoués avec les dépendances/Docker disponibles.

- Audit sécurité/intégrité/performance repris de bout en bout ; corrections JWT, redirections, médias privés, throttling live, validations, transactions et requêtes N+1.
- Indicateurs live **Participants / Mains / Live / Planifié** agrandis et centrés indépendamment du titre.
- Éditeur live transformé en **mini-IDE multi-fichiers** avec projets libres/POO et modèles React, Next.js, Django, Django REST Framework, FastAPI, Flask et Node/Express.
- Python multi-fichiers exécuté dans un Web Worker Pyodide isolé ; imports locaux, thèmes/coloration syntaxique et console redimensionnable.
- Correction définitive des permissions instructeur : création/modification de cours, leçons, ressources et PDF autonomes ; le champ admin `featured` est ignoré pour l’instructeur au lieu de bloquer la requête.
- Paiements rendus dynamiques : devises et passerelles administrables, drivers Stripe / YouCan Pay / GeniusPay / manuel et diagnostics de connexion.
- Mode test des passerelles réellement relié aux credentials sandbox ; environnement figé par commande avec `provider_sandbox`.
- Réconciliation et webhooks renforcés : montant, devise, référence, utilisateur, statut, signature et anti-rejeu selon le prestataire.
- Test email depuis les paramètres admin.
- Démarrage Docker ordonné par healthchecks backend/frontend pour supprimer les 502 pendant migrations/démarrage.
- Configuration Railway/Vercel et stockage S3-compatible documentés dans README/AUDIT.
- Tests de régression ajoutés pour contenu instructeur, configuration paiement et diagnostics admin.

---

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
- Une adresse correspondant déjà à un compte KalanPro obtient immédiatement l'accès invité ; une adresse sans compte reste en attente jusqu'à l'inscription avec le même email.
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
| Admin | admin@kalanpro.com | admin1234 |
| Instructeur (Dév. web) | sarah@kalanpro.com | instructor1234 |
| Instructeur (Data & IA) | koffi@kalanpro.com | instructor1234 |
| Instructeur (Design) | amina@kalanpro.com | instructor1234 |
| Étudiant | fatou@kalanpro.com | student1234 |
| Étudiant | jean@kalanpro.com | student1234 |
| Étudiant | aicha@kalanpro.com | student1234 |

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
- Ajout d’une vue **Séances live** avec filtres, accès à la salle KalanPro et rapports de présence
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
- Certificat de formation interactive configurable selon le **taux de présence réel** enregistré dans les séances KalanPro.
- Espace instructeur **Certificats** : configuration par contenu, candidats éligibles, délivrance individuelle, registre, révocation et réémission.
- Espace admin **Certificats** : paramètres globaux, surcharge par contenu, registre global, délivrance forcée exceptionnelle, révocation/réémission et activation de la vérification publique.
- Chaque certificat conserve un snapshot des informations au moment de l'émission et dispose d'un numéro ainsi que d'un code de vérification uniques.
- La vérification publique ne révèle pas l'adresse email de l'apprenant.
- `seed_demo` génère un certificat de démonstration pour **Fatou Ndiaye** afin de tester immédiatement le parcours apprenant.

## v36 — Vidéos non téléchargeables depuis l’interface

- Suppression des boutons **Télécharger** et **Ouvrir la source** du lecteur vidéo KalanPro.
- Le lecteur HTML5 annonce `nodownload` et `noremoteplayback`, désactive le glisser-déposer et le menu contextuel sur la zone vidéo.
- Les médias vidéo privés restent servis uniquement via des URLs signées et en `Content-Disposition: inline`, avec cache privé/no-store.
- Une navigation navigateur explicitement déclarée comme `document`, `iframe`, `object` ou `embed` vers un média vidéo privé est refusée ; les requêtes normales du lecteur `<video>` continuent de fonctionner.
- Les redirections S3 demandent une disposition `inline` et un cache privé/no-store quand le backend de stockage le permet.
- Ajout de tests de régression sur les en-têtes de streaming et le refus de navigation directe.

> Limite technique : un navigateur doit recevoir les octets d’une vidéo pour la lire. Sans DRM (Widevine/FairPlay/PlayReady), aucun site web ne peut empêcher absolument un utilisateur technique de capturer le flux réseau ou l’écran. v36 supprime et durcit les mécanismes de téléchargement ordinaires sans casser la lecture.

---

# v53 — Navigation par survol, domaines et performance catalogue

## Navigation

- La barre de navigation desktop utilise désormais des menus déroulants au **survol** et au focus clavier, dans l'esprit des grandes consoles SaaS.
- **Formations** ouvre un méga-menu vers Cours vidéo, PDF & Guides, Cohortes live et les principaux domaines.
- **Mentorat** et **Opportunités** possèdent également leurs sous-menus dédiés.
- Sur mobile, les mêmes informations restent accessibles via des groupes `<details>` repliables.

## Domaines et filtres

- Ajout d'une taxonomie métier `Domain` distincte des catégories : Technologie & Numérique, Data & IA, Design & Création, Business & Gestion, Bureautique & Productivité, etc.
- Nouvelle API publique `/api/catalog/domains/` et nouvelle migration `catalog.0006_domain_category_domain`.
- Les Cours, PDF et Cohortes peuvent être filtrés par **domaine**, puis par catégorie.
- Les filtres sont disponibles sur desktop **et** mobile.
- L'administration KalanPro permet maintenant de créer, ordonner, modifier et supprimer les domaines, puis d'affecter chaque catégorie à un domaine.

## Performance

- Suppression de plusieurs N+1 sur les listes Cours, PDF, Cohortes et Mentorat.
- Les cartes catalogue utilisent des serializers compacts et ne calculent plus inutilement le nombre de cours de chaque instructeur.
- Les listes de cours ne préchargent plus sections/leçons/PDF quand ces données ne sont pas affichées.
- Les cohortes utilisent un compteur d'inscrits annoté en SQL plutôt que plusieurs `COUNT()` par carte.
- Les créneaux de mentorat et leurs réservations sont préchargés en une fois.
- Ajout d'un cache serveur court pour les données publiques de catalogue malgré la CSP dynamique : listes 30–60 s, taxonomies 5 min.
- L'image hero passe d'environ **1,3 Mo à ~44 Ko WebP**.
- En développement Docker, `node_modules` n'est plus réinstallé à chaque redémarrage et Next.js utilise **Turbopack**.

## Tests

- Ajout de tests backend pour l'API Domain, le filtrage par domaine et la non-régression du nombre de requêtes SQL sur la liste de cours.
- Audit mobile et tests statiques de sécurité frontend conservés.
