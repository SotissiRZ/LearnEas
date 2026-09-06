# Validation v88 — Premium apprenant

Après extraction de l'archive :

```bash
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.dev.yml up -d --build

docker compose -f docker-compose.dev.yml exec backend python manage.py migrate
docker compose -f docker-compose.dev.yml exec backend python manage.py check
docker compose -f docker-compose.dev.yml exec backend python manage.py makemigrations --check --dry-run

docker compose -f docker-compose.dev.yml exec backend python manage.py test apps.payments
docker compose -f docker-compose.dev.yml exec backend python manage.py test

docker compose -f docker-compose.dev.yml exec frontend npm run test:ci
docker compose -f docker-compose.dev.yml exec frontend npm run build:check
```

Toujours sans `down -v` afin de conserver la base et les médias de développement.

## Résultat de référence hors dépendances Docker

- tests structurels frontend : **78/78** ;
- audit mobile : **133 fichiers inspectés, aucune alerte bloquante** ;
- compilation syntaxique Python : **OK** ;
- migrations v88 : parsing Python **OK**.

L'environnement de génération ne contient pas Django ni `node_modules`; les gates `manage.py check`, `makemigrations --check`, suite Django, `tsc` et build Next restent donc à confirmer dans Docker/CI avec les dépendances du projet installées.

## Scénarios manuels

1. Dans **Admin → Paramètres**, activer Premium et modifier le prix ; vérifier `/pricing`.
2. Dans **Admin → Contenus**, marquer un cours et un PDF comme `Premium`.
3. Vérifier qu'un instructeur ne peut pas forcer `premium_included=true` sur son propre contenu.
4. Acheter Premium depuis `/pricing` et vérifier la période de 30 jours dans le dashboard étudiant.
5. Filtrer `/courses?premium_included=true` et `/pdfs?premium_included=true`.
6. Ouvrir un contenu Premium et utiliser **Accéder avec Premium** ; vérifier que le droit possède une date d'expiration.
7. Acheter ensuite le même cours à l'unité ; vérifier que son accès devient permanent sans perte de progression.
8. Acheter deux périodes Premium successives ; vérifier que la seconde commence à la fin de la première.
9. Rembourser la première période ; vérifier que la seconde est recalée sans trou et que le contenu reste accessible jusqu'à la nouvelle échéance.
10. Rembourser la dernière couverture Premium ; vérifier que les droits Premium expirent mais que les achats à l'unité restent accessibles.
