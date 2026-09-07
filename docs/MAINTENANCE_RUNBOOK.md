# KalanPro — Runbook de maintenance

## 1. Routine quotidienne

### Santé globale

Admin → **Santé plateforme** ou :

```text
GET /api/ops/health/
```

Vérifier :

- PostgreSQL = OK ;
- Redis = OK ;
- queues Celery raisonnables ;
- stockage distant = OK ;
- HLS `failed` ou `processing` anormalement ancien ;
- anomalies paiement ;
- échecs email/WhatsApp ;
- tickets/modération en attente ;
- qualité live dégradée.

### Paiements

```bash
python manage.py reconcile_payments
```

Ne jamais marquer manuellement une commande `paid` uniquement pour faire disparaître une anomalie sans preuve fournisseur.

### Premium

```bash
python manage.py premium_revenue_report --json
```

Surveiller : `past_due`, `unsettled_periods`, allocations inversées.

## 2. Routine hebdomadaire

```bash
python manage.py rtc_capacity_report --json
python manage.py premium_revenue_report --json
```

- contrôler backups ;
- vérifier profondeur des queues ;
- vérifier objets multipart abandonnés ;
- vérifier coûts stockage/egress ;
- revoir erreurs récurrentes par `request_id` ;
- vérifier comptes admin récemment créés/modifiés.

## 3. Routine mensuelle

- restaurer une sauvegarde sur staging ;
- appliquer les mises à jour dépendances dans une branche dédiée ;
- exécuter tous les gates ;
- revoir volumes DB et index ;
- revoir analytics retention ;
- vérifier secrets expirants/tokens fournisseurs ;
- vérifier certificats DNS/HTTPS et domaine Resend ;
- vérifier Webhooks testés.

## 4. Mise à jour des dépendances

### Backend

1. créer branche maintenance ;
2. modifier `backend/requirements.txt` ;
3. reconstruire ;
4. exécuter :

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test apps.common apps.payments apps.accounts apps.formations
```

5. vérifier changelogs sécurité des dépendances majeures ;
6. déployer staging ;
7. smoke ;
8. production.

### Frontend

```bash
npm ci
npm run test:ci
npm run build:check
```

Ne pas faire de mise à jour majeure Next.js/React en production directe.

## 5. Migrations Django

Avant commit :

```bash
python manage.py makemigrations --check --dry-run
```

Si un changement de modèle est intentionnel :

```bash
python manage.py makemigrations
python manage.py migrate
```

Règles production :

- préférer migrations additives ;
- éviter rename/drop + code incompatible dans la même release ;
- sauvegarder avant migration sensible ;
- exécuter en Pre-deploy Railway ;
- ne jamais exécuter les migrations depuis plusieurs workers simultanément.

## 6. Celery

Queues :

- `default`
- `notifications`
- `media`

Si queue `media` monte :

1. vérifier worker vivant ;
2. vérifier CPU/RAM ;
3. vérifier ffmpeg ;
4. vérifier accès S3 ;
5. chercher tâches en retry/failed ;
6. n’augmenter la concurrence qu’après mesure.

`celery-beat` : une seule instance.

## 7. Médias / HLS

Symptômes fréquents :

- vidéo bloquée `processing` ;
- segments HLS 403/404 ;
- upload multipart non terminé ;
- PDF/image inaccessible.

Contrôles :

- `USE_S3=True` ;
- credentials bucket ;
- CORS du bucket ;
- expiration URL présignée ;
- worker `media` ;
- logs ffmpeg ;
- espace/quota fournisseur.

Migration anciens médias :

```bash
python manage.py migrate_local_media_to_storage --source /app/media
python manage.py migrate_local_media_to_storage --source /app/media --apply
```

## 8. Notifications

### Email

- vérifier `RESEND_ENABLED`/SMTP ;
- vérifier domaine expéditeur ;
- vérifier spam/bounces ;
- vérifier worker `notifications`.

### WhatsApp

- vérifier token Meta ;
- vérifier webhook ;
- vérifier `WHATSAPP_DRY_RUN=False` uniquement en prod ;
- vérifier templates/permissions côté Meta.

## 9. Paiements

```bash
python manage.py reconcile_payments
```

En cas de webhook manquant :

- vérifier signature/secrets ;
- vérifier logs Railway ;
- vérifier événement fournisseur ;
- utiliser réconciliation ;
- ne jamais fabriquer une référence fournisseur.

## 10. Premium

```bash
python manage.py premium_revenue_report --json
```

La V92 ne simule pas un débit récurrent hors session. `action_required`/`past_due` peut signifier que l’apprenant doit confirmer un nouveau checkout.

## 11. Live / WebRTC

```bash
python manage.py rtc_capacity_report --json
```

Si `sfu_recommended_sessions > 0`, analyser données réelles avant de déployer un SFU.

Qualité médiocre : vérifier TURN, RTT/perte, navigateur, réseau utilisateur, charge mesh.

## 12. Sécurité

- rotation régulière des secrets ;
- MFA sur Railway/Vercel/Git/fournisseurs ;
- permissions minimales ;
- aucun `.env` dans Git ;
- scan secrets en CI ;
- antivirus uploads actif en prod ;
- revoir admins et accès support/finance.

## 13. Docker local

Démarrer :

```bash
docker compose -f docker-compose.dev.yml up -d --build
```

Arrêter sans perte :

```bash
docker compose -f docker-compose.dev.yml down
```

**Ne pas ajouter `-v`.**

`make clean` est destructif car il supprime les volumes.
