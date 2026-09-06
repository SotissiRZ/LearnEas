# KalanPro v87 — Analytics produit & pilotage admin

v87 ajoute une couche d'analytics interne sans dépendance à un tracker tiers. Les indicateurs métier restent dérivés des tables de référence PostgreSQL ; la nouvelle table `analytics.ProductEvent` ne sert qu'aux signaux d'usage qui n'existent pas déjà ailleurs (pages vues, recherches, clics, lecture vidéo).

## Principes de confidentialité

- aucune query string n'est stockée ;
- les routes sensibles (`reset-password`, vérification email, retour checkout, login/register) ne sont pas tracées ;
- les recherches ne stockent jamais le texte saisi, uniquement la longueur et le type d'action ;
- les propriétés acceptées sont limitées à une whitelist technique ;
- l'identifiant de session navigateur est haché SHA-256 côté serveur ;
- les événements sont purgés automatiquement après `ANALYTICS_RETENTION_DAYS` (395 jours par défaut) ;
- paiements, candidatures, certificats et inscriptions restent mesurés directement depuis leurs tables métier.

## Dashboard administrateur

Nouvel onglet **Administration → Analytics** avec périodes 7/30/90/365 jours :

- inscriptions et utilisateurs actifs mesurés ;
- rétention de période à période ;
- commandes démarrées, paiements, échecs, remboursements, GMV et commission nette ;
- inscriptions cours/formations, PDF, mentorat, cours terminés et certificats ;
- candidatures, entretiens, offres et embauches ;
- tunnels commerce et recrutement ;
- activité quotidienne ;
- pages les plus consultées ;
- cours et formations les plus acquis ;
- export CSV administrateur.

## Événements produit

Événements v87 acceptés :

- `page_view`
- `search_submitted`
- `discovery_result_clicked`
- `recommendation_clicked`
- `course_viewed`
- `formation_viewed`
- `pdf_viewed`
- `opportunity_viewed`
- `video_started`
- `video_completed`

Les métriques produit commencent à s'accumuler à partir de v87. Les métriques métier historiques restent disponibles car elles sont recalculées depuis la base existante.

## Configuration

```env
PRODUCT_ANALYTICS_THROTTLE_RATE=300/hour
ANALYTICS_RETENTION_DAYS=395
```

En Docker dev, le throttle par défaut est plus élevé (`500/hour`).

## API

```text
POST /api/analytics/events/
GET  /api/analytics/admin/overview/?period=30
GET  /api/analytics/admin/export/?period=30
```

Les deux endpoints admin nécessitent le rôle `admin`.

## Migration

```text
analytics.0001_product_analytics_v87
```

Migration additive uniquement.
