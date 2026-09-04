# Certificats vérifiables LearnEas — v47

## Objectif

Un certificat LearnEas n'est plus seulement une page imprimable. Il devient une **preuve publique vérifiable** reliée à un registre serveur, avec QR code, numéro unique, état actuel et snapshot immuable des éléments pédagogiques au moment de l'émission.

> Un certificat LearnEas atteste les critères configurés sur la plateforme. Il ne devient pas automatiquement un diplôme d'État ni une qualification réglementée.

## Données figées lors de l'émission

Chaque nouveau certificat v47 enregistre notamment :

- nom du détenteur ;
- cours ou formation ;
- instructeur ;
- émetteur LearnEas / raison sociale et pays ;
- résultat ;
- date d'achèvement ;
- durée ;
- compétences attestées ;
- projets pratiques approuvés avec note, barème, validateur et date ;
- numéro de certificat ;
- UUID de vérification ;
- empreinte SHA-256 du snapshot public.

Les modifications ultérieures du cours, du portfolio ou des paramètres de la plateforme ne réécrivent pas ces preuves.

## Vérification publique

### URL directe

```text
/certificates/verify/<UUID>
```

### Recherche par numéro ou UUID

```http
GET /api/enrollments/certificates/lookup/?q=LE-CERT-2026-...
```

### API publique de vérification

```http
GET /api/enrollments/certificates/verify/<UUID>/
```

Aucun email, téléphone, identifiant de compte ou donnée privée de l'apprenant n'est exposé.

### QR code

```http
GET /api/enrollments/certificates/verify/<UUID>/qr/
```

Le QR encode uniquement l'URL publique de vérification. Il reste donc utile même après révocation : le scan affichera alors clairement l'état **Révoqué**.

## Révocation et réémission

Une révocation ne supprime jamais le certificat. Le registre conserve l'ancien numéro et l'ancien QR code.

Une réémission crée **un nouveau certificat**, un nouveau numéro et un nouveau UUID. L'ancien enregistrement reste consultable et pointe vers sa version de remplacement.

Cela évite le comportement dangereux qui consisterait à écraser silencieusement le certificat historique.

## Historique

`CertificateEvent` conserve les événements :

- `issued` ;
- `revoked` ;
- `expired` ;
- `reissued`.

Le détenteur, l'instructeur et l'administration voient cet historique sur la fiche privée du certificat. Celery Beat matérialise automatiquement les certificats arrivés à expiration chaque heure afin que le registre et les contraintes SQL restent cohérents.

## Empreinte SHA-256

`credential_digest` est une empreinte technique du snapshot public. Elle permet de détecter une altération accidentelle ou non autorisée des données du certificat.

Elle ne doit pas être présentée comme une signature électronique qualifiée ou une preuve blockchain.

## Migration

```bash
docker compose exec backend python manage.py migrate
```

La migration `enrollments.0005_verifiable_credentials` :

1. transforme le lien certificat/inscription afin de conserver plusieurs versions historiques ;
2. ajoute les snapshots de preuves ;
3. ajoute l'empreinte ;
4. crée le journal `CertificateEvent` ;
5. conserve et enrichit les certificats déjà présents.

## Dépendance

Le backend utilise `qrcode==8.2` pour produire les PNG de vérification.
