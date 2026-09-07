# Validation V91

## Validation effectuée avant packaging

- `npm run test:unit` : **103/103 tests réussis**.
- `npm run audit:mobile` : **136 fichiers inspectés, aucune alerte bloquante**.
- `python -m compileall -q backend` : OK.
- Parsing AST Python : OK.
- Aucun modèle métier modifié et aucune migration ajoutée.
- Le SFU n'est pas marqué actif : `active_adapter=False` tant qu'un adaptateur réel n'est pas implémenté.
- La télémétrie qualité utilise le cache avec TTL, sans stockage permanent.

L'environnement de génération ne contient pas Django ni les dépendances npm, donc les tests API Django et le `tsc --noEmit` complet doivent être exécutés dans Docker.

## Gates Docker recommandés

```bash
docker compose -f docker-compose.dev.yml exec backend python manage.py check
docker compose -f docker-compose.dev.yml exec backend python manage.py makemigrations --check --dry-run
docker compose -f docker-compose.dev.yml exec backend python manage.py test apps.formations apps.common

docker compose -f docker-compose.dev.yml exec frontend npm run test:ci
docker compose -f docker-compose.dev.yml exec frontend npm run build:check
```

## Vérification live V91

Avec deux comptes dans une séance :

1. vérifier caméra/micro et signalisation WebSocket ;
2. couper brièvement le réseau d'un participant puis le rétablir avant le délai d'abandon ;
3. vérifier que le pair tente un ICE restart au lieu d'être immédiatement supprimé ;
4. vérifier `Administration → Santé plateforme` après plusieurs intervalles de télémétrie ;
5. exécuter :

```bash
docker compose -f docker-compose.dev.yml exec backend python manage.py rtc_capacity_report --json
```

## TURN staging

Tester au minimum deux chemins TURN : UDP et TLS/TCP. Pour confirmer qu'un réseau passe réellement par TURN, utiliser temporairement :

```env
RTC_ICE_TRANSPORT_POLICY=relay
```

Revenir ensuite à `all` sauf besoin réseau explicite.

## Décision SFU

Ne déployer le SFU que si les tests réels montrent au moins un de ces signaux récurrents :

- salles au-dessus de `RTC_SFU_RECOMMEND_THRESHOLD` ;
- dégradation de RTT/perte à mesure que le nombre de participants augmente ;
- bande passante montante trop élevée sur les mobiles ;
- `rtc_capacity_report --fail-on-sfu-recommended` échoue régulièrement en staging/usage réel.
