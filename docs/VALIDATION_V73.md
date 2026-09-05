# Validation KalanPro v73

## Rôle Entreprise / Recruteur

- `User.Role.EMPLOYER` ajouté avec migration dédiée.
- Inscription publique limitée à `student` ou `employer` ; impossible de s'auto-attribuer `admin` ou `instructor`.
- L'inscription employeur crée le `EmployerProfile` dans la même transaction, statut `pending`.
- Les anciens utilisateurs possédant un `EmployerProfile` mais encore `student` sont migrés vers `employer`.
- Dashboard `/dashboard/employer` protégé par rôle employeur.
- Publication et vivier restent conditionnés à `EmployerProfile.status=approved`.
- Un employeur ne peut pas déposer de candidature candidat ni ouvrir un profil candidat.
- Retrait administratif du rôle employeur : profil suspendu et offres publiées clôturées, historique conservé.

## Contrôles exécutés dans l'environnement d'assemblage

- Parsing/compilation syntaxique Python : OK (223 fichiers).
- Graphe de migrations : 60 migrations, aucun cycle détecté statiquement.
- `npm run test:roles` : 4/4.
- `npm run test:security` : 4/4.
- `npm run test:performance` : 5/5.
- `npm run audit:mobile` : 121 fichiers, aucune alerte bloquante.

## Release gate Docker

L'environnement d'assemblage ne contient pas Django installé directement sur l'hôte ; les checks Django complets doivent donc être exécutés dans le conteneur du projet :

```bash
docker compose -f docker-compose.dev.yml up --build
docker compose -f docker-compose.dev.yml exec backend python manage.py check
docker compose -f docker-compose.dev.yml exec backend python manage.py showmigrations
docker compose -f docker-compose.dev.yml exec backend python manage.py test
```
