from django.conf import settings
from django.db.models import Count, Avg, Sum
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from .models import AIConversation, AIMessage, AISettings, AIUsage, AIKnowledgeChunk, AIEvaluationCase, AIActionLog, AIDraft
from .serializers import AIConversationListSerializer, AIConversationDetailSerializer, AISettingsSerializer
from .services import answer, quota_state, role_enabled, estimate_cost_eur
from .tools import create_action_proposal, serialize_action, execute_action, reject_action
from .evaluation import seed_evaluation_cases, run_evaluation


class AIThrottle(UserRateThrottle):
    scope = "ai"


class AIConversationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        qs = AIConversation.objects.filter(user=self.request.user)
        cfg = AISettings.load()
        # Quand l'historique est désactivé, les anciennes conversations ne
        # sont plus exposées dans la liste. Une conversation active peut
        # cependant continuer via son identifiant pendant la session courante.
        if self.action == "list" and not cfg.history_enabled:
            return qs.none()
        archived = self.request.query_params.get("archived")
        if archived in {"true", "false"}:
            qs = qs.filter(archived=(archived == "true"))
        qs = qs.annotate(messages_count=Count("messages"))
        if self.action == "retrieve":
            qs = qs.prefetch_related("messages")
        return qs

    def get_serializer_class(self):
        return AIConversationDetailSerializer if self.action == "retrieve" else AIConversationListSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        conversation = self.get_object()
        conversation.archived = True
        conversation.save(update_fields=["archived", "updated_at"])
        return Response(AIConversationListSerializer(conversation).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def status_view(request):
    cfg = AISettings.load()
    return Response({
        "enabled": bool(cfg.enabled and role_enabled(request.user, cfg)),
        "rag_enabled": cfg.rag_enabled,
        "history_enabled": cfg.history_enabled,
        "tools_enabled": cfg.tools_enabled,
        "dry_run": bool(getattr(settings, "AI_DRY_RUN", False)),
        "provider_ready": bool(getattr(settings, "AI_API_KEY", "") and (cfg.default_model or getattr(settings, "AI_CHAT_MODEL", ""))),
        "model": cfg.default_model or getattr(settings, "AI_CHAT_MODEL", ""),
        "quota": quota_state(request.user, cfg),
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([AIThrottle])
def chat_view(request):
    cfg = AISettings.load()
    if not cfg.enabled or not role_enabled(request.user, cfg):
        return Response({"detail": "L'assistant IA n'est pas activé pour ce profil."}, status=status.HTTP_403_FORBIDDEN)
    quota = quota_state(request.user, cfg)
    if not quota["unlimited"] and quota["remaining"] <= 0:
        return Response({"detail": "Votre quota IA mensuel est atteint.", "quota": quota}, status=status.HTTP_429_TOO_MANY_REQUESTS)

    question = str(request.data.get("message") or "").strip()
    if not question:
        return Response({"message": ["Ce champ est obligatoire."]}, status=status.HTTP_400_BAD_REQUEST)
    if len(question) > 4000:
        return Response({"message": ["Le message ne peut pas dépasser 4000 caractères."]}, status=status.HTTP_400_BAD_REQUEST)
    page_context = request.data.get("page_context") or {}
    if not isinstance(page_context, dict):
        return Response({"page_context": ["Format invalide."]}, status=status.HTTP_400_BAD_REQUEST)
    response_style = str(request.data.get("response_style") or "normal")
    if response_style not in {"short", "normal", "detailed"}:
        response_style = "normal"

    conversation_id = request.data.get("conversation_id")
    created_new = not bool(conversation_id)
    if conversation_id:
        conversation = AIConversation.objects.filter(pk=conversation_id, user=request.user).first()
        if not conversation:
            return Response({"detail": "Conversation introuvable."}, status=status.HTTP_404_NOT_FOUND)
    else:
        conversation = AIConversation.objects.create(user=request.user, title=question[:80])

    user_message = AIMessage.objects.create(conversation=conversation, role=AIMessage.Role.USER, content=question)
    if cfg.history_enabled:
        history_rows = list(conversation.messages.exclude(pk=user_message.pk).order_by("-created_at")[:cfg.max_history_messages])
        history_rows.reverse()
        history = [{"role": row.role, "content": row.content} for row in history_rows]
    else:
        history = []

    try:
        result = answer(request.user, question, history, page_context, response_style, cfg)
    except Exception as exc:
        user_message.delete()
        if created_new and not conversation.messages.exists():
            conversation.delete()
        return Response({"detail": f"Assistant IA indisponible : {str(exc)[:240]}"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    sources = [
        {"id": chunk.id, "title": chunk.title, "type": chunk.source_type, "path": chunk.source_path, "metadata": chunk.metadata, "score": float(getattr(chunk, "_ai_relevance_score", 0) or 0)}
        for chunk in result["chunks"]
    ]
    message = AIMessage.objects.create(
        conversation=conversation,
        role=AIMessage.Role.ASSISTANT,
        content=result["content"],
        sources=sources,
        provider=result["provider"],
        model=result["model"],
        prompt_tokens=result["prompt_tokens"],
        completion_tokens=result["completion_tokens"],
    )
    action_rows = []
    for pending in result.get("pending_actions") or []:
        try:
            action_rows.append(create_action_proposal(
                request.user, conversation, message, pending["tool_name"], pending.get("arguments") or {}
            ))
        except Exception:
            # Une proposition invalide ne doit pas faire échouer une réponse IA déjà générée.
            continue
    actions = [serialize_action(row) for row in action_rows]
    if actions:
        message.actions = actions
        message.save(update_fields=["actions"])
    conversation.context_preview = result["context_preview"]
    if conversation.title == "Nouvelle conversation":
        conversation.title = question[:80]
    conversation.save(update_fields=["context_preview", "title", "updated_at"])
    AIUsage.objects.create(
        user=request.user,
        conversation=conversation,
        provider=result["provider"],
        model=result["model"],
        prompt_tokens=result["prompt_tokens"],
        completion_tokens=result["completion_tokens"],
        latency_ms=result["latency_ms"],
        rag_chunks=len(sources),
        estimated_cost_eur=estimate_cost_eur(result["prompt_tokens"], result["completion_tokens"], cfg),
    )
    return Response({
        "conversation_id": conversation.id,
        "message": {"id": message.id, "role": message.role, "content": message.content, "sources": sources, "actions": actions, "provider": message.provider, "model": message.model, "created_at": message.created_at},
        "quota": quota_state(request.user, cfg),
        "context": result["context_preview"],
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def action_confirm_view(request, token):
    action = AIActionLog.objects.select_related("message", "conversation").filter(confirmation_token=token, user=request.user).first()
    if not action:
        return Response({"detail": "Action IA introuvable."}, status=status.HTTP_404_NOT_FOUND)
    try:
        result = execute_action(action)
    except (ValueError, PermissionError) as exc:
        return Response({"detail": str(exc), "action": serialize_action(action)}, status=status.HTTP_400_BAD_REQUEST)
    serialized = serialize_action(action)
    if action.message_id:
        existing = list(action.message.actions or [])
        actions = [serialized if item.get("token") == str(action.confirmation_token) else item for item in existing]
        if not any(item.get("token") == str(action.confirmation_token) for item in existing):
            actions.append(serialized)
        action.message.actions = actions
        action.message.save(update_fields=["actions"])
    return Response({"action": serialized, "result": result})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def action_reject_view(request, token):
    action = AIActionLog.objects.select_related("message").filter(confirmation_token=token, user=request.user).first()
    if not action:
        return Response({"detail": "Action IA introuvable."}, status=status.HTTP_404_NOT_FOUND)
    try:
        reject_action(action)
    except ValueError as exc:
        return Response({"detail": str(exc), "action": serialize_action(action)}, status=status.HTTP_400_BAD_REQUEST)
    serialized = serialize_action(action)
    if action.message_id:
        existing = list(action.message.actions or [])
        actions = [serialized if item.get("token") == str(action.confirmation_token) else item for item in existing]
        if not any(item.get("token") == str(action.confirmation_token) for item in existing):
            actions.append(serialized)
        action.message.actions = actions
        action.message.save(update_fields=["actions"])
    return Response({"action": serialized})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def drafts_view(request):
    qs = AIDraft.objects.filter(user=request.user).select_related("course")
    kind = str(request.query_params.get("kind") or "").strip()
    if kind in {AIDraft.Kind.QUIZ, AIDraft.Kind.COURSE_OUTLINE}:
        qs = qs.filter(kind=kind)
    rows = qs[:50]
    return Response([{
        "id": row.id, "kind": row.kind, "title": row.title, "payload": row.payload,
        "course_id": row.course_id, "course_title": row.course.title if row.course else "",
        "created_at": row.created_at, "updated_at": row.updated_at,
    } for row in rows])


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def admin_settings_view(request):
    if request.user.role != "admin":
        return Response({"detail": "Accès administrateur requis."}, status=status.HTTP_403_FORBIDDEN)
    cfg = AISettings.load()
    if request.method == "PATCH":
        serializer = AISettingsSerializer(cfg, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
    return Response(AISettingsSerializer(cfg).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def message_feedback_view(request, message_id: int):
    message = AIMessage.objects.select_related("conversation").filter(
        pk=message_id, conversation__user=request.user, role=AIMessage.Role.ASSISTANT
    ).first()
    if not message:
        return Response({"detail": "Réponse IA introuvable."}, status=status.HTTP_404_NOT_FOUND)
    feedback = str(request.data.get("feedback") or "").strip().lower()
    comment = str(request.data.get("comment") or "").strip()[:1000]
    if feedback in {"", "clear"}:
        message.feedback = ""
        message.feedback_comment = ""
        message.feedback_at = None
    elif feedback in {AIMessage.Feedback.HELPFUL, AIMessage.Feedback.UNHELPFUL}:
        message.feedback = feedback
        message.feedback_comment = comment
        message.feedback_at = timezone.now()
    else:
        return Response({"feedback": ["Valeur attendue : helpful, unhelpful ou clear."]}, status=status.HTTP_400_BAD_REQUEST)
    message.save(update_fields=["feedback", "feedback_comment", "feedback_at"])
    return Response({
        "id": message.id,
        "feedback": message.feedback,
        "feedback_comment": message.feedback_comment,
        "feedback_at": message.feedback_at,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def admin_evaluate_rag_view(request):
    if request.user.role != "admin":
        return Response({"detail": "Accès administrateur requis."}, status=status.HTTP_403_FORBIDDEN)
    seed = bool(request.data.get("seed", True))
    top_k = request.data.get("top_k", 6)
    limit = request.data.get("limit", 50)
    try:
        created = seed_evaluation_cases(int(limit)) if seed else 0
        result = run_evaluation(request.user, top_k=int(top_k), limit=int(limit))
    except (TypeError, ValueError):
        return Response({"detail": "Paramètres d'évaluation invalides."}, status=status.HTTP_400_BAD_REQUEST)
    result["created"] = created
    return Response(result)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_actions_view(request):
    if request.user.role != "admin":
        return Response({"detail": "Accès administrateur requis."}, status=status.HTTP_403_FORBIDDEN)
    rows = AIActionLog.objects.select_related("user").order_by("-created_at")[:50]
    return Response([{
        "id": row.id, "user_email": row.user.email, "tool": row.tool_name, "label": row.label,
        "status": row.status, "error": row.error, "created_at": row.created_at, "executed_at": row.executed_at,
    } for row in rows])


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_metrics_view(request):
    if request.user.role != "admin":
        return Response({"detail": "Accès administrateur requis."}, status=status.HTTP_403_FORBIDDEN)
    start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly = AIUsage.objects.filter(created_at__gte=start)
    usage = monthly.aggregate(
        prompt_tokens=Sum("prompt_tokens"),
        completion_tokens=Sum("completion_tokens"),
        avg_latency_ms=Avg("latency_ms"),
        avg_rag_chunks=Avg("rag_chunks"),
        estimated_cost_eur=Sum("estimated_cost_eur"),
    )
    feedback_qs = AIMessage.objects.filter(role=AIMessage.Role.ASSISTANT).exclude(feedback="")
    feedback_total = feedback_qs.count()
    helpful = feedback_qs.filter(feedback=AIMessage.Feedback.HELPFUL).count()
    eval_enabled = AIEvaluationCase.objects.filter(enabled=True)
    eval_ran = eval_enabled.filter(last_passed__isnull=False)
    eval_passed = eval_ran.filter(last_passed=True).count()
    return Response({
        "conversations": AIConversation.objects.count(),
        "messages": AIMessage.objects.count(),
        "usage_requests": AIUsage.objects.count(),
        "knowledge_chunks": AIKnowledgeChunk.objects.count(),
        "users_with_ai": AIUsage.objects.values("user_id").distinct().count(),
        "month_requests": monthly.count(),
        "month_prompt_tokens": int(usage["prompt_tokens"] or 0),
        "month_completion_tokens": int(usage["completion_tokens"] or 0),
        "month_estimated_cost_eur": float(usage["estimated_cost_eur"] or 0),
        "avg_latency_ms": int(usage["avg_latency_ms"] or 0),
        "avg_rag_chunks": round(float(usage["avg_rag_chunks"] or 0), 2),
        "feedback_total": feedback_total,
        "helpful_rate": round((helpful / feedback_total * 100), 1) if feedback_total else None,
        "eval_cases": eval_enabled.count(),
        "eval_pass_rate": round((eval_passed / eval_ran.count() * 100), 1) if eval_ran.count() else None,
        "actions_proposed": AIActionLog.objects.filter(status=AIActionLog.Status.PROPOSED).count(),
        "actions_executed": AIActionLog.objects.filter(status=AIActionLog.Status.EXECUTED).count(),
        "actions_failed": AIActionLog.objects.filter(status=AIActionLog.Status.FAILED).count(),
        "drafts": AIDraft.objects.count(),
    })
