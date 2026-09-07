# KalanPro — Diagnostic de performance

## 1. Ne pas confondre dev et production

`next dev --turbopack` dans Docker Desktop sur un dossier Windows peut être nettement plus lent qu’un build production. La première visite d’une route peut compiler la page et prendre plusieurs secondes.

Pour juger les performances réelles : utiliser `npm run build:check`, staging Vercel/Railway, puis les runners de release.

## 2. Diagnostic rapide local

```bash
docker stats
```

Puis :

```bash
curl -w "\n%{time_total}s\n" http://localhost:8000/api/health/live/
curl -w "\n%{time_total}s\n" http://localhost:8000/api/health/ready/
```

Dans Chrome : F12 → Network → Fetch/XHR.

Déterminer si le délai vient :

- du document Next ;
- d’un endpoint `/api` ;
- d’un média ;
- d’une cascade de requêtes frontend.

## 3. Gates de performance

Local :

```bash
npm run release:qualify:dev
```

Staging/prod :

```bash
RELEASE_BASE_URL=https://... RELEASE_BACKEND_URL=https://... npm run release:smoke:prod
```

`release:load` fournit p50/p95/p99, taux d’erreur et RPS.

## 4. Backend lent

Vérifier :

- PostgreSQL CPU/IO/connexions ;
- requêtes N+1 ;
- endpoints admin lourds ;
- cache Redis ;
- fournisseurs externes dans le chemin synchrone ;
- taille réponses/pagination ;
- logs excessifs.

Ne pas activer le logging SQL complet en production de façon permanente.

## 5. Frontend lent

Vérifier :

- First Load JS ;
- composants dynamiques lourds ;
- appels API séquentiels ;
- images non optimisées ;
- pages dashboard qui chargent plusieurs modules inutiles ;
- erreurs/retries réseau.

Pages historiquement plus lourdes dans V93 : apprentissage, fiche cours, édition cours, review admin, live.

## 6. HLS lent

- CDN/origine ;
- taille segments ;
- bitrate ;
- distance bucket/utilisateur ;
- erreurs Range/CORS ;
- URLs signées expirées ;
- faible connexion : tester mode éco ≤ 360p/audio-only.

## 7. Celery lent

Admin → Santé plateforme : profondeur queues.

Si backlog :

- tâches trop longues ;
- worker absent ;
- provider externe lent ;
- concurrence trop faible ;
- retry storm ;
- CPU/RAM insuffisants.

## 8. WebRTC lent / mauvaise qualité

```bash
python manage.py rtc_capacity_report --json
```

Vérifier :

- RTT ;
- perte paquet ;
- participants mesh ;
- TURN disponible ;
- CPU navigateur ;
- bitrate adaptatif.

Ne passer à SFU que lorsque les données de capacité le justifient.

## 9. Windows + Docker Desktop

Pour améliorer le dev local si nécessaire :

- allouer suffisamment CPU/RAM à Docker ;
- éviter antivirus/indexeur sur `node_modules`/`.next` ;
- éviter de juger la latence production avec hot reload ;
- si I/O reste problématique, envisager le dépôt dans WSL2/Linux pour le développement.

## 10. Critères d’alerte initiaux

À adapter après mesures réelles :

- readiness non 2xx ;
- taux erreur > 1 % sur charge de référence ;
- p95 API/public pages en hausse > 2× baseline ;
- queue media > seuil `OPERATIONS_QUEUE_WARNING_DEPTH` ;
- paiements `past_due`/stale en croissance ;
- HLS failed > 0 récurrent ;
- pertes WebRTC élevées ou SFU recommandé sur salles actives.
