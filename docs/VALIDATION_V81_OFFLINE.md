# Validation v81 — visionnage réel et vidéo hors connexion

## Garanties ajoutées

- Une vidéo hébergée par KalanPro ne peut pas être validée tant que sa durée serveur est inconnue.
- Une fois la durée connue, le seuil de complétion du cours (90 % par défaut, configurable 50–100 %) est vérifié côté backend.
- Un simple seek ne crédite pas de temps regardé.
- Les heartbeats trop rapprochés sont plafonnés par le temps mural.
- La progression hors connexion est signée et le client ne supprime que le temps effectivement crédité par le serveur.
- Les copies hors connexion sont opt-in par leçon, générées en basse définition et bornées en taille.
- IndexedDB est cloisonné par utilisateur ; les anciennes copies v1 non cloisonnées sont purgées lors du passage au schéma local v2.
- La bibliothèque `/offline-player.html` et son JS sont mises en cache par Service Worker pour un redémarrage sans réseau.
- La bibliothèque possède une CSP dédiée : aucun script inline, aucun accès réseau applicatif.

## Contrôles statiques exécutés

- Python compileall : OK.
- 68 migrations, aucune collision/dépendance manquante/cycle ; les 2 migrations v81 sont additives.
- 143 fichiers TS/TSX parsés sans erreur syntaxique.
- 44/44 tests frontend statiques : OK.
- Audit mobile : 127 fichiers, aucune alerte bloquante.
- Scan de secrets : OK.
- Docker Compose YAML : OK.
- JavaScript du Service Worker et du lecteur offline : syntaxe OK.

## Validation Docker requise

```bash
docker compose -f docker-compose.dev.yml exec backend python manage.py migrate
docker compose -f docker-compose.dev.yml exec backend python manage.py check
docker compose -f docker-compose.dev.yml exec backend python manage.py makemigrations --check --dry-run
docker compose -f docker-compose.dev.yml exec backend python manage.py test apps.catalog apps.enrollments
docker compose -f docker-compose.dev.yml exec backend python manage.py test
docker compose -f docker-compose.dev.yml exec frontend npm run test:ci
docker compose -f docker-compose.dev.yml exec frontend npm run build:check
```

## Test manuel hors connexion

1. Activer `Hors ligne` sur une leçon vidéo depuis l'espace instructeur.
2. Attendre que le worker média termine la préparation.
3. En apprenant, télécharger la leçon depuis le lecteur.
4. Ouvrir `Bibliothèque hors ligne` une première fois.
5. Couper complètement le réseau puis recharger `/offline-player.html`.
6. Vérifier la lecture de la copie locale et la reprise.
7. Regarder une partie de la vidéo hors ligne, reconnecter Internet puis rouvrir le cours.
8. Vérifier que la progression est resynchronisée et qu'une validation avant le seuil est refusée.
