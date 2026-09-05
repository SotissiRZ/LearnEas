# Validation runtime v78 — correctifs après premier passage Docker

Le premier passage Docker de v78 a identifié :

- deux migrations de synchronisation de state Django manquantes ;
- quatre erreurs/failures de tests liées au verrou PostgreSQL du mentorat, à la confirmation admin des paiements externes et à des fixtures devenues obsolètes ;
- une erreur TypeScript dans `app/assistant/drafts/page.tsx`.

Cette révision conserve le numéro **v78** : il s'agit de corrections de stabilisation avant livraison stable, sans changement destructif de données.

À revalider dans Docker :

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test apps.opportunities apps.payments
npm run build
```
