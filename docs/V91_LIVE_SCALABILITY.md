# KalanPro V91 — Scalabilité live, WebRTC/TURN et préparation SFU

V91 renforce la salle live existante sans remplacer sa pile temps réel. Django Channels reste le canal de signalisation, l'API DRF reste la source de vérité et WebRTC reste en **mesh** tant qu'aucun adaptateur SFU réel n'est déployé.

## 1. Résilience ICE

Avant V91, un pair en état `disconnected` ou `failed` était retiré presque immédiatement. Sur un réseau mobile, un changement 4G/Wi‑Fi ou une courte perte de couverture pouvait donc faire disparaître la vidéo alors que la connexion pouvait récupérer.

V91 ajoute :

- délai de grâce configurable `RTC_DISCONNECT_GRACE_SECONDS` ;
- `RTCPeerConnection.restartIce()` avant abandon ;
- offre avec `{ iceRestart: true }` ;
- initiateur déterministe (plus petit `user_id`) pour réduire la glare d'offres simultanées ;
- suppression définitive uniquement si la connexion reste `failed/disconnected` après la seconde fenêtre de grâce.

## 2. TURN/STUN production

Le backend accepte désormais plusieurs URLs :

```env
RTC_STUN_URLS=stun:stun1.example.com:3478,stun:stun2.example.com:3478
RTC_TURN_URLS=turn:turn.example.com:3478?transport=udp,turns:turn.example.com:5349?transport=tcp
```

Les anciennes variables `RTC_STUN_URL` et `RTC_TURN_URL` restent compatibles.

Avec coturn REST, `RTC_TURN_SECRET` génère toujours un username expirant et un credential HMAC côté backend. Le secret n'est jamais envoyé au navigateur.

`RTC_ICE_TRANSPORT_POLICY=relay` permet un diagnostic/forçage TURN sur les réseaux très restrictifs ; la valeur normale reste `all`.

## 3. Pression du mesh et bitrate

Le mesh implique environ `N × (N-1)` flux pair-à-pair. V91 ne prétend donc pas rendre le mesh illimité.

Variables :

```env
RTC_MESH_SOFT_LIMIT=6
RTC_SFU_RECOMMEND_THRESHOLD=7
RTC_VIDEO_MAX_BITRATE_KBPS=900
RTC_AUDIO_MAX_BITRATE_KBPS=64
```

Quand le nombre de participants augmente, le frontend réduit progressivement le bitrate vidéo envoyé. La salle affiche aussi un avertissement lorsque le seuil mesh est dépassé.

Ce seuil est un **signal opérationnel**, pas une limite dure : une classe n'est pas expulsée automatiquement.

## 4. Qualité WebRTC éphémère

Chaque client agrège périodiquement `RTCPeerConnection.getStats()` :

- RTT ;
- jitter ;
- perte de paquets ;
- débit sortant disponible ;
- nombre de pairs ;
- classe locale `good / fair / poor / unknown`.

Le résultat est envoyé à :

```text
POST /api/sessions/<id>/quality/
```

Les données sont stockées **uniquement dans le cache Redis**, avec TTL (`RTC_QUALITY_TTL_SECONDS`, 180 s par défaut). Aucune migration et aucun historique permanent de qualité réseau ne sont créés.

L'organisateur peut lire l'instantané de sa salle avec :

```text
GET /api/sessions/<id>/quality/
```

Le back-office `Santé plateforme` agrège les sessions live actives : rapports reçus, qualité faible, RTT moyen et perte moyenne.

## 5. Contrat SFU sans fausse intégration

`/api/sessions/<id>/room/` expose un `rtc_policy` :

- `topology: mesh` ;
- `recommended_topology` ;
- seuil mesh/SFU ;
- état de configuration SFU ;
- politique ICE ;
- pool ICE ;
- délai de récupération ;
- intervalle de télémétrie ;
- bitrates maximaux.

Même si `RTC_SFU_URL` est configuré, V91 conserve `topology: mesh`. Le back-office indique `SFU prêt` mais `active_adapter=False`. Cette distinction évite de présenter une fonctionnalité comme active avant l'intégration réelle d'un protocole/provider (LiveKit, mediasoup, Janus, etc.).

## 6. Rapport de décision SFU

Commande :

```bash
python manage.py rtc_capacity_report --json
```

Elle analyse uniquement les salles live actives et rapporte : nombre de participants, seuil mesh, recommandation de topologie et métriques WebRTC éphémères.

Pour rendre la recommandation bloquante dans un test de staging :

```bash
python manage.py rtc_capacity_report --fail-on-sfu-recommended
```

L'objectif est de décider le déploiement d'un SFU avec des données réelles plutôt qu'avec une hypothèse de capacité.

## 7. Variables V91

```env
RTC_STUN_URLS=
RTC_TURN_URLS=
RTC_MESH_SOFT_LIMIT=6
RTC_SFU_RECOMMEND_THRESHOLD=7
RTC_SFU_URL=
RTC_ICE_TRANSPORT_POLICY=all
RTC_ICE_CANDIDATE_POOL_SIZE=2
RTC_DISCONNECT_GRACE_SECONDS=8
RTC_QUALITY_INTERVAL_SECONDS=10
RTC_QUALITY_TTL_SECONDS=180
RTC_VIDEO_MAX_BITRATE_KBPS=900
RTC_AUDIO_MAX_BITRATE_KBPS=64
```

## Ce que V91 ne fait pas

- elle ne déploie pas coturn à votre place ;
- elle ne déploie pas un SFU ;
- elle ne remplace pas Channels par un protocole propriétaire ;
- elle ne stocke pas durablement les statistiques de réseau ;
- elle n'augmente pas artificiellement la capacité mesh annoncée.
