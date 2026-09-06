# Validation KalanPro v83

## Contrôles exécutés dans l'environnement de génération

- tests frontend statiques : **53/53 OK** ;
- audit responsive/mobile : **129 fichiers**, aucune alerte bloquante ;
- parsing TypeScript/TSX : **146 fichiers**, 0 erreur de syntaxe ;
- compilation Python : **249 fichiers**, 0 erreur de syntaxe ;
- scan de secrets : **OK** ;
- Docker Compose dev/prod : **YAML OK** ;
- entrypoint shell : **OK** ;
- graphe de migrations : **72 migrations**, 0 dépendance manquante, 0 collision, 0 cycle ;
- **219 fonctions de tests backend** sont présentes dans le dépôt.

Les nouveaux tests backend couvrent notamment : ordre de la liste d'attente, expiration d'une priorité, réinscription après expiration, confidentialité de la file côté instructeur, débit/recrédit d'un pass, reprogrammation, validité du pass, conflits de rendez-vous entre offres, règles récurrentes et achat/remboursement d'un pack.

## Validation runtime à exécuter dans Docker

Django n'est pas installé dans l'environnement de génération (`ModuleNotFoundError: django`), donc `manage.py check`, les migrations réelles et la suite Django ne sont pas annoncés comme exécutés ici.

Après extraction :

```powershell
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.dev.yml up -d --build

docker compose -f docker-compose.dev.yml exec backend python manage.py migrate
docker compose -f docker-compose.dev.yml exec backend python manage.py check
docker compose -f docker-compose.dev.yml exec backend python manage.py makemigrations --check --dry-run

docker compose -f docker-compose.dev.yml exec backend python manage.py test apps.formations apps.payments
docker compose -f docker-compose.dev.yml exec backend python manage.py test

docker compose -f docker-compose.dev.yml exec frontend npm run test:ci
docker compose -f docker-compose.dev.yml exec frontend npm run build:check
```

Ne pas utiliser `docker compose down -v` : cette option supprimerait les volumes, notamment PostgreSQL.

## Tests fonctionnels recommandés

1. Remplir une cohorte, inscrire deux apprenants en liste d'attente, libérer une place et vérifier que le plus ancien reçoit la priorité.
2. Laisser expirer une priorité et vérifier que la personne suivante est proposée sans survente.
3. Acheter un pack de mentorat en paiement de test, réserver une séance avec le pass, annuler avant le délai et vérifier le recrédit.
4. Reprogrammer un rendez-vous confirmé et vérifier que seule la nouvelle salle reste accessible.
5. Créer deux offres du même mentor avec des créneaux qui se chevauchent : après réservation de l'une, l'autre doit devenir indisponible.
6. Créer une règle récurrente, générer les créneaux, modifier/désactiver la règle et vérifier que les anciens créneaux libres deviennent inactifs sans toucher aux rendez-vous déjà réservés.

## Correctif de démarrage Docker intégré

La sonde Docker du backend utilise désormais `/api/health/live/` sur `127.0.0.1`. La sonde `/api/health/ready/` continue de vérifier PostgreSQL et Redis mais n'est plus utilisée comme critère de vie du conteneur. Redis possède sa propre healthcheck en développement et le worker média est démarré explicitement.

Si le backend ne démarre toujours pas, le diagnostic à exécuter est :

```powershell
docker compose -f docker-compose.dev.yml ps
docker compose -f docker-compose.dev.yml logs --tail=200 backend
```

La seconde commande expose alors une éventuelle erreur de migration/import réelle au lieu d'un simple `backend unhealthy`.

## Correctif runtime backend — OFFLINE_VIDEO_*

Le démarrage Docker pouvait boucler avant `migrate` avec `NameError: name 'os' is not defined` dans `learneas/settings.py`. Les quatre paramètres `OFFLINE_VIDEO_*` utilisent désormais `python-decouple` (`config`) comme le reste de la configuration. Un test statique de non-régression vérifie ce point.

