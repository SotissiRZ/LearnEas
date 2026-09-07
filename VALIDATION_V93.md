# Validation V93 — Production Go-Live

## Contrôles exécutés dans l'environnement de génération

- tests structurels frontend : **115/115 OK** ;
- audit mobile : **136 fichiers, aucune alerte bloquante** ;
- préflight frontend avec URLs HTTPS factices : **OK** ;
- compilation syntaxique Python (`compileall`) : **OK** ;
- syntaxe Node des scripts V93 et `next.config.js` : **OK** ;
- YAML : `docker-compose.dev.yml`, `docker-compose.yml`, `.github/workflows/ci.yml` : **OK** ;
- scan secrets haute confiance : **OK**.

## Contrôle non exécutable ici

Django n'est pas installé dans l'environnement de génération. Les commandes runtime suivantes doivent être exécutées dans le conteneur Docker utilisateur :

```bash
python manage.py migrate
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test apps.common apps.payments apps.accounts apps.formations
python manage.py production_preflight --json
```

Le `production_preflight` réel doit être exécuté seulement avec les vraies variables staging/production ; il est normal qu'il échoue tant que S3/R2, email, paiement, TURN ou ClamAV ne sont pas configurés.
