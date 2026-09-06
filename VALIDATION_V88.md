# Validation V88 — Support & modération

Résultat structurel local avant packaging : **78 tests / 78 réussis / 0 échec**, audit mobile **135 fichiers / 0 alerte bloquante**, parsing Python/TSX/YAML OK.

## Gates structurels

```bash
cd frontend
npm run test:unit
npm run audit:mobile
npm run typecheck
```

## Gates Django / Docker recommandés

```bash
docker compose -f docker-compose.dev.yml exec backend python manage.py migrate
docker compose -f docker-compose.dev.yml exec backend python manage.py check
docker compose -f docker-compose.dev.yml exec backend python manage.py makemigrations --check --dry-run
docker compose -f docker-compose.dev.yml exec backend python manage.py test apps.support
```

## Scénarios manuels prioritaires

1. Étudiant crée un ticket, puis vérifie qu'un autre étudiant ne peut pas le lire.
2. Admin s'assigne le ticket, répond, puis l'étudiant voit la notification et répond.
3. Étudiant ferme le ticket ; un nouveau message est ensuite refusé sur ce ticket fermé.
4. Utilisateur signale un cours ; un second signalement actif de la même cible est refusé.
5. Admin classe le signalement, renseigne l'action et la note ; le journal de décision est créé.
6. Vérifier que les onglets FAQ et Avis fonctionnent toujours dans `Support & modération`.

## Correctif V88.4 — labels Opportunités legacy

Le dernier `tsc --noEmit` Docker ne remontait plus que deux erreurs dans `lib/opportunities.ts` : les labels `mission` et `archived` manquaient alors que ces valeurs font partie du contrat courant.

V88.4 réintègre ce fichier legacy directement dans l’archive et complète les deux maps exhaustives. Validation locale :

- `npm run test:unit` : **86/86** ;
- `npm run audit:mobile` : **136 fichiers, aucune alerte bloquante** ;
- compilation TypeScript stricte ciblée `types/opportunities.ts` + `lib/opportunities.ts` : **OK** ;
- compilation syntaxique Python : **OK**.

Gate final Docker :

```bash
docker compose -f docker-compose.dev.yml exec frontend npm run test:ci
```
