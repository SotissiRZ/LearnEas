# KalanPro AI — Phase 1

## Périmètre livré

La Phase 1 ajoute un assistant contextuel unique pour les profils apprenant, instructeur et administrateur :

- chat persistant ;
- historique des conversations ;
- contexte automatique de la page ;
- contexte précis de la leçon actuellement ouverte ;
- RAG sur cours, transcriptions, PDF liés aux cours et PDF autonomes ;
- contrôle d'accès aux sources privées ;
- quotas mensuels configurables par rôle ;
- administration IA dans le dashboard KalanPro et Django Admin ;
- journal d'usage (requêtes, tokens déclarés par le fournisseur, latence, chunks RAG) ;
- mode `AI_DRY_RUN=True` pour tester localement sans consommer de crédits.

## Architecture

```text
Frontend Next.js
   -> /api/ai/chat/
      -> Auth JWT
      -> quota
      -> Context Builder
      -> RAG autorisé
      -> historique court
      -> API LLM compatible
      -> conversation + usage
```

Les clés fournisseur ne sont jamais envoyées au navigateur et ne sont pas enregistrées en base.

## Variables serveur

```env
AI_API_KEY=
AI_API_BASE=https://api.openai.com/v1
AI_CHAT_MODEL=
AI_PROVIDER_NAME=Compatible API
AI_HTTP_TIMEOUT=60
AI_DRY_RUN=False
AI_INDEX_ASYNC=True
AI_REBUILD_INDEX_ON_BOOT=False
AI_THROTTLE_RATE=30/min
```

En local Docker (`docker-compose.dev.yml`), `AI_DRY_RUN=True` et `AI_REBUILD_INDEX_ON_BOOT=True` sont activés par défaut afin de tester l'interface sans coût. En production, `AI_DRY_RUN=False` est le défaut : une clé et un modèle réels doivent être configurés côté serveur. L'index n'est reconstruit au boot que s'il est vide.

## Index RAG

Une reconstruction manuelle peut être lancée avec :

```bash
docker compose exec backend python manage.py rebuild_ai_index
```

Les nouveaux cours, leçons/transcripts et PDF sont ensuite réindexés automatiquement. En production, l'indexation de fichier peut passer par Celery.

Les PDF scannés sans couche texte ne sont pas OCRisés dans cette phase : ils restent indexés par leurs métadonnées/description jusqu'à l'ajout éventuel d'un pipeline OCR.

## Permissions RAG

Un utilisateur peut récupérer :

- les métadonnées publiques des cours publiés ;
- les leçons preview publiques ;
- le contenu complet d'un cours acquis ;
- les cours dont il est instructeur ;
- les PDF gratuits ;
- les PDF achetés ;
- toutes les sources s'il est administrateur.

Les contenus d'autres utilisateurs ne sont jamais ajoutés au prompt sans droit d'accès.

## Interface

- bouton flottant `KalanPro AI` pour les utilisateurs connectés ;
- espace complet `/assistant` ;
- historique et suppression des conversations ;
- réponses courtes / normales / détaillées ;
- sources KalanPro cliquables ;
- quota restant visible ;
- assistant masqué dans la salle live jusqu'à la future Phase IA 3.

## Administration

`Dashboard admin -> Assistant IA` permet de modifier :

- activation globale ;
- RAG ;
- historique ;
- activation par rôle ;
- quotas mensuels ;
- modèle ;
- température ;
- limite de réponse ;
- taille d'historique ;
- nombre de chunks RAG ;
- instructions globales.

La clé API reste exclusivement dans Railway / `.env`.


## Limites volontaires de la Phase 1

- Le RAG utilise la recherche plein texte PostgreSQL avec priorité au contexte de page ; une couche d'embeddings/vectorielle pourra être ajoutée ensuite sans changer l'API frontend.
- Les PDF scannés sans couche texte ne sont pas OCRisés.
- Les actions qui modifient KalanPro (publier, acheter, candidater, envoyer un message, etc.) restent hors périmètre jusqu'à la Phase 2.
- L'assistant est volontairement masqué dans les salles live ; l'assistance de séance est prévue en Phase 3.
