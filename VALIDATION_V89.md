# Validation V89

## Gates statiques exécutés lors de la construction

- `npm run test:unit` : 91/91.
- `npm run audit:mobile` : aucune alerte bloquante.
- `python -m compileall -q backend`.
- parsing YAML Compose/CI.
- parsing syntaxique TypeScript des fichiers admin modifiés.
- scan de secrets du dépôt.

## Gates Docker à exécuter avant de marquer V89 livrable production

```bash
docker compose -f docker-compose.dev.yml exec backend python manage.py check
docker compose -f docker-compose.dev.yml exec backend python manage.py makemigrations --check --dry-run
docker compose -f docker-compose.dev.yml exec backend python manage.py test apps.common
docker compose -f docker-compose.dev.yml exec frontend npm run test:ci
docker compose -f docker-compose.dev.yml exec frontend npm run build:check
```

Avec un bucket de staging configuré, vérifier en plus :

1. upload multipart d'une vidéo > taille d'un bloc ;
2. lecture HLS ;
3. média privé via URL signée ;
4. image publique via CDN si `PUBLIC_MEDIA_BASE_URL` est activé ;
5. `Admin → Santé plateforme` ;
6. `migrate_local_media_to_storage` d'abord sans `--apply`, puis sur un petit préfixe de test.

Ne jamais utiliser `docker compose down -v` pour une validation ordinaire : cette option supprime les volumes locaux PostgreSQL/médias.
