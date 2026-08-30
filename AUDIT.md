# Audit technique LearnEas — v9

Date : 2026-08-29

## Résumé exécutif

La v9 a été revue sur les axes sécurité, intégrité métier, tests, performance, UX/accessibilité et
responsive mobile-first. Les défauts bloquants identifiés pendant l’audit ont été corrigés avant
archivage. Le produit reste une application à déployer avec une configuration d’infrastructure
correcte : HTTPS, Stripe/webhook, SMTP et TURN ne peuvent pas être fournis par le code seul.

## Sécurité

### Corrigé
- API JWT uniquement ; l’admin Django conserve session + CSRF.
- Rotation et blacklist des refresh tokens, access token 1 h.
- Throttling global via Redis pour auth, reset, checkout et médias.
- Validation Django des mots de passe.
- `SECRET_KEY` de développement et `ALLOWED_HOSTS=*` refusés avec `DEBUG=False`.
- Swagger/OpenAPI non exposés en production.
- Vidéos, PDF et sous-titres privés : URL signée 5 minutes puis `X-Accel-Redirect` nginx.
- Stripe Checkout + webhook signé ; un paiement payant ne peut pas être auto-confirmé par le client en production.
- Réservation temporaire des places live pendant Stripe Checkout.
- Permissions objet revues sur contenus, commentaires, messagerie, séances, finance et certificats.
- En-têtes nginx : nosniff, frame deny, referrer policy, CSP et Permissions-Policy.
- Processus backend/Celery lancé comme utilisateur applicatif non privilégié après bootstrap.

### Risques résiduels / infrastructure
- P1 : activer HTTPS réel et renseigner des secrets de production avant exposition Internet.
- P1 : configurer `STRIPE_WEBHOOK_SECRET`; sans webhook valide, aucune commande payante ne doit être délivrée.
- P1 : configurer un TURN de production pour la fiabilité WebRTC sur réseaux mobiles restrictifs.
- P2 : ajouter antivirus/scan de fichiers si les uploads deviennent ouverts à grande échelle.
- P2 : migrer les refresh tokens de `localStorage` vers une architecture BFF/cookie HttpOnly pour durcir encore le modèle XSS.

## Tests

- Tests unitaires/intégration Django/DRF présents dans les apps.
- Régressions ajoutées sur achat→accès, CSRF/session admin, permissions instructeur/admin, médias,
  live, certificats, messagerie, finance et réservation de places.
- CI GitHub Actions : `check`, `makemigrations --check`, migrations PostgreSQL, tests Django,
  `npm ci`, audit mobile, build Next.js et validation Compose.
- Limite de l’environnement de génération : pas de téléchargement des dépendances ; le build réel
  et les tests runtime doivent être exécutés par Docker/CI.

## Performance

- `select_related`/`prefetch_related` sur les listes à fort trafic et agrégations SQL pour KPI/notes.
- Index ajoutés : contenus publiés/catégorie, instructeur/publication, formations statut/publication,
  commandes statut/date et utilisateur/statut, réservations formation/expiration.
- gzip nginx, cache statique, streaming interne des médias privés.
- Images de couverture/avatars optimisées en WebP à l’upload lorsque le pipeline le permet.
- Vidéo avec `preload=metadata`; WebRTC réduit sur mobile.

### Recommandation de montée en charge
Pour une audience importante sur réseaux mobiles, transcoder les vidéos en HLS adaptatif
(360p/480p/720p) et les servir via CDN. Pour des classes live nombreuses, remplacer le maillage
P2P par un SFU (LiveKit/Janus/mediasoup/Jitsi) plutôt que multiplier les flux pair-à-pair.

## Mobile / UX / accessibilité

La cible prioritaire est 320–412 px :
- navigation dashboards adaptée au tactile ;
- formulaires mono-colonne puis enrichissement progressif aux breakpoints ;
- cibles tactiles ~44 px et champs 16 px sur mobile ;
- tableaux contenus dans des zones scrollables ;
- curriculum du cours en tiroir mobile ;
- cartes/grilles 1 colonne sur petits écrans ;
- footer légal responsive ;
- lecteurs vidéo/PDF utilisables en plein écran ;
- images lazy/async lorsqu’elles passent par `<img>`.

Le script `npm run audit:mobile` détecte les régressions statiques courantes. Un test visuel réel
reste recommandé sur Chrome Android et Safari iOS aux largeurs 320, 360, 390, 412 et 768 px.

## Paiements Afrique francophone

Stripe carte est le moyen réellement intégré. Mobile Money/PayPal restent désactivés tant qu’un
prestataire n’est pas connecté. Pour le marché cible, prévoir CinetPay, Flutterwave, PayDunya,
PawaPay ou intégrations opérateurs selon les pays, avec webhook signé et réconciliation serveur.

## Checklist avant production

- [ ] `.env` avec SECRET_KEY aléatoire et mots de passe DB forts.
- [ ] `DEBUG=False`, `ALLOWED_HOSTS` exacts, HTTPS et `USE_HTTPS=True`.
- [ ] Stripe secret + webhook secret + webhook enregistré.
- [ ] SMTP configuré.
- [ ] TURN configuré et testé sur réseau mobile réel.
- [ ] `docker compose up --build` réussi.
- [ ] `python manage.py test` réussi.
- [ ] `npm run build` réussi.
- [ ] Tests manuels 320/360/390/412 px et tablette.
- [ ] Sauvegardes PostgreSQL et médias vérifiées.
