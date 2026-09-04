# LearnEas v50 — Correctifs P1 sécurité, performance et exploitation

## Authentification

- Le refresh JWT n'est plus renvoyé dans le JSON et n'est plus stocké dans `localStorage`.
- Le refresh est conservé dans un cookie `HttpOnly`, `Secure` en production et `SameSite=Lax` par défaut.
- L'access token n'est plus persistant : il reste uniquement en mémoire de l'onglet et expire après 15 minutes.
- Après rechargement, le frontend renouvelle l'access token via le cookie puis valide `/auth/me/` avant d'afficher une zone protégée.
- Le refresh et le logout valident l'en-tête `Origin` lorsqu'il est présent afin de protéger les endpoints basés sur le cookie.
- Login, inscription, refresh et logout gèrent le cookie côté serveur. Le refresh HttpOnly reste stable entre les renouvellements afin d’éviter les courses multi-onglets ; logout et changement de mot de passe le blacklistent.
- Le changement de mot de passe révoque les refresh tokens et supprime le cookie courant.

### Vercel + Railway

Configuration recommandée côté Vercel :

```env
NEXT_PUBLIC_API_URL=/api
API_PROXY_TARGET=https://VOTRE-BACKEND.up.railway.app
INTERNAL_API_URL=https://VOTRE-BACKEND.up.railway.app/api
```

Le navigateur reste ainsi sur l'origine Vercel pour `/api/*` et ne dépend pas des cookies tiers.

Côté Railway :

```env
DEBUG=False
USE_HTTPS=True
AUTH_REFRESH_COOKIE_SECURE=True
AUTH_REFRESH_COOKIE_SAMESITE=Lax
CORS_ALLOWED_ORIGINS=https://VOTRE-FRONTEND.vercel.app
FRONTEND_URL=https://VOTRE-FRONTEND.vercel.app
```

## Performance SQL

- Matching opportunités : profil candidat, compétences portfolio, projets vérifiés, certificats et IDs de candidatures sont calculés une seule fois par sérialisation de liste, au lieu d'être relus pour chaque offre.
- Projets apprenant : inscription et remise du viewer sont préchargées via `Prefetch`, supprimant les deux requêtes par projet des `SerializerMethodField`.

## Recruteurs

Une entreprise approuvée repasse automatiquement en `pending` si le recruteur change son identité sensible : nom, site web, pays ou logo. Ses offres disparaissent alors du catalogue public jusqu'à nouvelle approbation, sans supprimer les candidatures historiques.

## Fichiers uploadés

La validation ne repose plus seulement sur le nom du fichier :

- PDF : signature `%PDF-` obligatoire ;
- DOC/XLS/PPT : signature OLE réelle ;
- DOCX/XLSX/PPTX : ZIP valide + structure Office attendue ;
- ZIP : archive valide, sans traversal `../`, avec limite anti-zip-bomb ;
- TXT/CSV : rejet des contenus binaires avec octets NUL ;
- VTT : en-tête `WEBVTT` obligatoire.

### Antivirus

Un client ClamAV/clamd INSTREAM sans dépendance Python supplémentaire est disponible. En production, `MALWARE_SCAN_REQUIRED=True` par défaut : les PDF/Office/ZIP sont refusés si l'antivirus n'est pas disponible, sauf décision explicite de désactiver ce garde-fou.

```env
MALWARE_SCAN_ENABLED=True
MALWARE_SCAN_REQUIRED=True
CLAMAV_HOST=hostname-du-service-clamd
CLAMAV_PORT=3310
CLAMAV_TIMEOUT_SECONDS=30
```

## Médias privés

- URL fichier privé classique : expiration par défaut ramenée de 12 h à 15 min.
- HLS conserve une durée séparée de 6 h afin qu'une longue vidéo ne casse pas en cours de lecture.

```env
PRIVATE_MEDIA_TOKEN_MAX_AGE=900
HLS_MEDIA_TOKEN_MAX_AGE=21600
```

## Celery

Trois files logiques :

- `media` : ffprobe/ffmpeg/HLS ;
- `notifications` : WhatsApp/rappels ;
- `default` : tâches courtes générales.

Docker démarre désormais un `celery_media_worker` séparé avec concurrence 1 et prefetch 1. Le worker standard n'écoute que `default,notifications`. Sur Railway, créer au minimum deux services Worker avec les mêmes commandes.

## Contrôles exécutables dans l'environnement d'audit

- compilation Python de tous les modules ;
- parsing syntaxique TypeScript des fichiers modifiés ;
- syntaxe `next.config.js` ;
- parsing YAML de `docker-compose.yml` ;
- audit mobile : 112 fichiers, aucune alerte bloquante.

La suite Django et `next build` doivent encore être exécutés dans Docker/CI avec les dépendances installées.
