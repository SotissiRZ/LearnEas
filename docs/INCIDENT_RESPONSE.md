# KalanPro — Réponse aux incidents

## 1. Niveaux

| Niveau | Exemple | Objectif |
|---|---|---|
| P0 | fuite de données, corruption financière massive, site totalement indisponible | action immédiate |
| P1 | paiements bloqués, login global cassé, DB instable | rétablissement prioritaire |
| P2 | fonction importante dégradée, HLS/WhatsApp/live partiellement indisponible | correction rapide |
| P3 | bug isolé, problème UX, incident sans impact critique | traitement normal |

## 2. Première réponse

1. confirmer l’incident ;
2. noter heure, environnement, version déployée ;
3. conserver logs et `request_id` ;
4. identifier dernier changement ;
5. décider rollback ou correction ;
6. éviter toute manipulation de données irréversible sans backup.

## 3. Site indisponible

Vérifier :

```text
Frontend /healthz
Backend /api/health/live/
Backend /api/health/ready/
```

Si live OK et ready KO : dépendance DB/Redis probablement en cause.

Si frontend KO mais backend OK : incident Vercel/build/domain.

## 4. PostgreSQL indisponible

- vérifier Railway PostgreSQL ;
- connexion `DATABASE_URL` ;
- saturation connexions ;
- stockage/quota ;
- migration bloquée ;
- ne pas redémarrer en boucle tous les services sans diagnostic.

Readiness 503 est attendu pendant la panne.

## 5. Redis indisponible

Impact possible :

- cache ;
- Channels/WebSocket ;
- Celery ;
- télémétrie live éphémère.

La donnée métier PostgreSQL doit rester intacte.

## 6. Paiement en anomalie

1. trouver commande et tentative ;
2. consulter fournisseur ;
3. consulter logs/webhook ;
4. exécuter :

```bash
python manage.py reconcile_payments
```

5. ne pas supprimer ledger/audit ;
6. corriger par mécanismes d’état/remboursement prévus.

## 7. Upload/HLS cassé

- vérifier S3/R2 ;
- worker `media` ;
- ffmpeg ;
- URL présignée ;
- CORS bucket ;
- timeout ;
- capacité CPU/RAM.

## 8. Emails/WhatsApp absents

- worker notifications ;
- provider ;
- secrets ;
- domaines/templates ;
- spam/bounces ;
- webhook Meta.

## 9. Live/WebRTC cassé

- API session ;
- WebSocket ;
- TURN ;
- réseau utilisateur ;
- `rtc_capacity_report` ;
- qualité RTT/perte.

## 10. Incident sécurité

En cas de secret exposé :

1. révoquer/rotater immédiatement ;
2. redeployer services concernés ;
3. auditer logs d’usage ;
4. vérifier données potentiellement accessibles ;
5. conserver preuve ;
6. suivre obligations légales/contractuelles applicables.

En cas de `.env` committé : supprimer du repo courant ne suffit pas ; considérer le secret compromis et le rotater.

## 11. Rollback

Frontend : rollback Vercel vers déploiement sain.

Backend : rollback Railway vers build sain.

DB : ne restaurer que si nécessaire ; un rollback applicatif ne doit pas automatiquement revenir en arrière sur une migration additive déjà appliquée.

## 12. Postmortem

Après P0/P1 :

- impact ;
- timeline ;
- cause racine ;
- pourquoi les protections n’ont pas suffi ;
- actions correctives ;
- propriétaire + échéance ;
- test de non-régression ajouté.
