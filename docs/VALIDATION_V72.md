# Validation KalanPro v72

## Régression corrigée

En v71, le proxy same-origin Next.js normalisait les URL et envoyait les routes API Django sans slash final. Les requêtes GET recevaient un 301, tandis que les POST (login/refresh) échouaient avec `RuntimeError` car Django `APPEND_SLASH` ne peut pas rediriger un POST tout en conservant son corps.

## Correction

- Rewrite API upstream : `${apiProxyTarget}/api/:path*/`.
- Les appels frontend conservent leurs chemins DRF slashés.
- Le message de login distingue désormais identifiants invalides et panne serveur/réseau.

## Données

Aucune migration ni modification destructive. Les comptes, cours, paiements, certificats et autres données restent inchangés.
