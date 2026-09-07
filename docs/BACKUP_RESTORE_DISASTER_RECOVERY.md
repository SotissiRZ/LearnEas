# KalanPro — Sauvegarde, restauration et reprise après sinistre

## 1. Objectifs

Les sauvegardes couvrent en priorité :

1. PostgreSQL ;
2. médias S3/R2 ;
3. configuration/secrets via plateformes ;
4. code/version Git ;
5. fournisseurs externes et webhooks documentés.

Redis n’est pas la source de vérité métier et n’est pas restauré comme PostgreSQL.

## 2. Sauvegarde PostgreSQL KalanPro

Commande :

```bash
python manage.py backup_database --upload --delete-local-after-upload
```

Elle crée un dump custom PostgreSQL et l’envoie sous :

```text
backups/database/kalanpro-YYYYMMDDTHHMMSSZ.dump
```

Le stockage utilisé est `default_storage`, donc S3/R2 en production.

### Avant opération risquée

Toujours sauvegarder avant :

- migration destructive ;
- gros import ;
- modification financière ;
- intervention manuelle SQL ;
- changement majeur de version PostgreSQL.

## 3. Vérification de sauvegarde

Une sauvegarde n’est considérée valide que si :

- commande terminée avec succès ;
- objet présent ;
- taille non nulle ;
- restauration testée périodiquement sur staging.

Ne jamais attendre un incident pour tester `pg_restore`.

## 4. Restauration

### Depuis stockage privé

```bash
python manage.py restore_database \
  --storage-key backups/database/<fichier>.dump \
  --confirm
```

### Depuis fichier local

```bash
python manage.py restore_database /chemin/backup.dump --confirm
```

La commande utilise `pg_restore --clean --if-exists` : elle est destructive au niveau logique de la base cible.

## 5. Procédure PRA

### Étape A — qualifier l’incident

- corruption DB ?
- migration incorrecte ?
- simple bug applicatif ?
- suppression utilisateur isolée ?

Un bug applicatif seul ne justifie généralement pas une restauration globale.

### Étape B — stopper les écritures

Selon incident :

- mettre application en maintenance ;
- stopper workers susceptibles d’écrire ;
- conserver logs et preuves.

### Étape C — capturer l’état actuel

Créer si possible un dump de l’état incident avant restauration, pour analyse forensic et récupération ciblée.

### Étape D — restaurer sur staging d’abord

Tester backup choisi :

- migrations cohérentes ;
- comptes ;
- commandes/paiements ;
- Premium ;
- certificats ;
- relations médias.

### Étape E — production

Restaurer uniquement avec validation explicite du responsable technique/métier.

### Étape F — validation

```bash
python manage.py check
python manage.py release_gate --strict-infra --deploy --production --json
```

Puis smoke frontend/backend.

## 6. Médias S3/R2

Le bucket doit avoir :

- versioning si disponible/économiquement acceptable ;
- lifecycle documenté ;
- protection suppression accidentelle ;
- accès privé ;
- politique de backup/réplication selon criticité.

Les sauvegardes DB ne contiennent pas les bytes des médias S3.

## 7. RPO/RTO proposés

À valider par le métier :

| Composant | RPO cible | RTO cible |
|---|---:|---:|
| PostgreSQL | ≤ 24 h, idéalement PITR | 1–4 h |
| S3/R2 | selon versioning/réplication | 1–4 h |
| Frontend Vercel | code Git, quasi 0 | < 30 min |
| Backend Railway | code Git, quasi 0 | < 60 min |
| Redis | non critique comme source de vérité | < 30 min |

## 8. Test PRA trimestriel

1. choisir un backup réel ;
2. restaurer dans environnement isolé ;
3. exécuter migrations/checks ;
4. vérifier données financières ;
5. vérifier médias ;
6. chronométrer ;
7. documenter écarts ;
8. corriger le runbook.
