# Validation v80

## Contrôles exécutés hors Docker

- 39/39 tests frontend statiques : OK
- audit mobile : 125 fichiers, aucune alerte bloquante
- parsing Python : 241 fichiers, 0 erreur
- parsing TypeScript/TSX : 138 fichiers, 0 erreur
- migrations : 66, 0 dépendance manquante, 0 collision de préfixe
- 199 fonctions de test backend détectées

## Validation runtime requise

L'environnement de génération ne dispose pas du runtime Docker complet du projet. Avant de déclarer v80 stable, exécuter dans Docker :

```bash
python manage.py migrate
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
npm run test:ci
npm run build:check
python manage.py reconcile_payments
```

## Scénarios live à valider avec le compte marchand

- paiement Mobile Money réussi ;
- paiement refusé ;
- paiement retardé/pending puis confirmé ;
- webhook dupliqué ;
- webhook reçu après redémarrage du backend ;
- incohérence montant ;
- incohérence devise ;
- timeout prestataire ;
- réconciliation d'une commande pending ;
- remboursement selon les capacités de l'intégration activée.
