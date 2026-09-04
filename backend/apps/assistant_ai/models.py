import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models


class AISettings(models.Model):
    enabled = models.BooleanField(default=True)
    rag_enabled = models.BooleanField(default=True)
    history_enabled = models.BooleanField(default=True)
    tools_enabled = models.BooleanField(default=True)
    student_enabled = models.BooleanField(default=True)
    instructor_enabled = models.BooleanField(default=True)
    admin_enabled = models.BooleanField(default=True)
    default_model = models.CharField(max_length=120, blank=True, help_text="Vide = modèle défini par AI_CHAT_MODEL dans l'environnement.")
    student_monthly_limit = models.PositiveIntegerField(default=20)
    instructor_monthly_limit = models.PositiveIntegerField(default=100)
    admin_monthly_limit = models.PositiveIntegerField(default=500)
    max_history_messages = models.PositiveSmallIntegerField(default=12)
    max_context_chunks = models.PositiveSmallIntegerField(default=6)
    max_output_tokens = models.PositiveIntegerField(default=1200)
    temperature = models.DecimalField(max_digits=3, decimal_places=2, default=0.30)
    input_cost_per_million_eur = models.DecimalField(max_digits=10, decimal_places=4, default=0, help_text="Coût estimé du modèle pour 1M tokens d'entrée.")
    output_cost_per_million_eur = models.DecimalField(max_digits=10, decimal_places=4, default=0, help_text="Coût estimé du modèle pour 1M tokens de sortie.")
    custom_system_prompt = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuration Assistant IA"
        verbose_name_plural = "Configuration Assistant IA"

    def save(self, *args, **kwargs):
        self.pk = 1
        self.student_monthly_limit = max(int(self.student_monthly_limit), 0)
        self.instructor_monthly_limit = max(int(self.instructor_monthly_limit), 0)
        self.admin_monthly_limit = max(int(self.admin_monthly_limit), 0)
        self.max_history_messages = min(max(int(self.max_history_messages), 2), 40)
        self.max_context_chunks = min(max(int(self.max_context_chunks), 1), 12)
        self.max_output_tokens = min(max(int(self.max_output_tokens), 128), 8000)
        self.temperature = min(max(Decimal(str(self.temperature or 0)), Decimal("0")), Decimal("1"))
        self.input_cost_per_million_eur = max(Decimal(str(self.input_cost_per_million_eur or 0)), Decimal("0"))
        self.output_cost_per_million_eur = max(Decimal(str(self.output_cost_per_million_eur or 0)), Decimal("0"))
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Assistant IA KalanPro"


class AIConversation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_conversations")
    title = models.CharField(max_length=120, default="Nouvelle conversation")
    context_preview = models.JSONField(default=dict, blank=True)
    archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [models.Index(fields=["user", "archived", "updated_at"], name="ai_conv_user_arch_idx")]

    def __str__(self):
        return f"{self.user.email} · {self.title}"


class AIMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user", "Utilisateur"
        ASSISTANT = "assistant", "Assistant"

    class Feedback(models.TextChoices):
        HELPFUL = "helpful", "Utile"
        UNHELPFUL = "unhelpful", "À améliorer"

    conversation = models.ForeignKey(AIConversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=20, choices=Role.choices)
    content = models.TextField()
    sources = models.JSONField(default=list, blank=True)
    actions = models.JSONField(default=list, blank=True)
    provider = models.CharField(max_length=80, blank=True)
    model = models.CharField(max_length=120, blank=True)
    prompt_tokens = models.PositiveIntegerField(default=0)
    completion_tokens = models.PositiveIntegerField(default=0)
    feedback = models.CharField(max_length=20, choices=Feedback.choices, blank=True)
    feedback_comment = models.CharField(max_length=1000, blank=True)
    feedback_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["conversation", "created_at"], name="ai_msg_conv_created_idx")]

    def __str__(self):
        return f"{self.role} · {self.conversation_id}"


class AIKnowledgeChunk(models.Model):
    class SourceType(models.TextChoices):
        COURSE = "course", "Cours"
        LESSON = "lesson", "Leçon / transcript"
        PDF_RESOURCE = "pdf_resource", "PDF de cours"
        PDF_PRODUCT = "pdf_product", "PDF autonome"

    source_type = models.CharField(max_length=30, choices=SourceType.choices)
    source_id = models.PositiveIntegerField()
    chunk_index = models.PositiveSmallIntegerField(default=0)
    title = models.CharField(max_length=240)
    content = models.TextField()
    source_path = models.CharField(max_length=500, blank=True)
    course = models.ForeignKey("catalog.Course", on_delete=models.CASCADE, null=True, blank=True, related_name="ai_chunks")
    pdf_product = models.ForeignKey("catalog.PDFProduct", on_delete=models.CASCADE, null=True, blank=True, related_name="ai_chunks")
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="ai_knowledge_chunks")
    is_public = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["source_type", "source_id", "chunk_index"]
        constraints = [
            models.UniqueConstraint(fields=["source_type", "source_id", "chunk_index"], name="uniq_ai_source_chunk")
        ]
        indexes = [
            models.Index(fields=["source_type", "source_id"], name="ai_chunk_source_idx"),
            models.Index(fields=["course", "is_public"], name="ai_chunk_course_pub_idx"),
            models.Index(fields=["pdf_product", "is_public"], name="ai_chunk_pdf_pub_idx"),
        ]

    def __str__(self):
        return f"{self.get_source_type_display()} · {self.title} · {self.chunk_index}"


class AIUsage(models.Model):
    request_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_usage")
    conversation = models.ForeignKey(AIConversation, on_delete=models.SET_NULL, null=True, blank=True, related_name="usage_entries")
    provider = models.CharField(max_length=80, blank=True)
    model = models.CharField(max_length=120, blank=True)
    prompt_tokens = models.PositiveIntegerField(default=0)
    completion_tokens = models.PositiveIntegerField(default=0)
    latency_ms = models.PositiveIntegerField(default=0)
    rag_chunks = models.PositiveSmallIntegerField(default=0)
    estimated_cost_eur = models.DecimalField(max_digits=12, decimal_places=6, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "created_at"], name="ai_usage_user_date_idx")]

    def __str__(self):
        return f"{self.user.email} · {self.created_at:%Y-%m-%d}"


class AIEvaluationCase(models.Model):
    question = models.CharField(max_length=500)
    expected_source_type = models.CharField(max_length=30, choices=AIKnowledgeChunk.SourceType.choices)
    expected_source_id = models.PositiveIntegerField()
    enabled = models.BooleanField(default=True)
    notes = models.CharField(max_length=500, blank=True)
    last_passed = models.BooleanField(null=True, blank=True)
    last_rank = models.PositiveSmallIntegerField(null=True, blank=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["question", "expected_source_type", "expected_source_id"], name="uniq_ai_eval_case")
        ]

    def __str__(self):
        return self.question[:80]


class AIDraft(models.Model):
    class Kind(models.TextChoices):
        QUIZ = "quiz", "Quiz"
        COURSE_OUTLINE = "course_outline", "Plan de cours"
        MENTOR_PLAN = "mentor_plan", "Plan de mentorat"
        INTERVIEW_RUBRIC = "interview_rubric", "Grille d’entretien"
        CV_IMPROVEMENT = "cv_improvement", "Amélioration CV"
        COVER_LETTER = "cover_letter", "Lettre de motivation"
        LEARNING_GAP_PLAN = "learning_gap_plan", "Plan de compétences"
        INTERVIEW_PREP = "interview_prep", "Préparation entretien"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_drafts")
    kind = models.CharField(max_length=30, choices=Kind.choices)
    title = models.CharField(max_length=220)
    payload = models.JSONField(default=dict)
    course = models.ForeignKey("catalog.Course", on_delete=models.SET_NULL, null=True, blank=True, related_name="ai_drafts")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [models.Index(fields=["user", "kind", "-updated_at"], name="ai_draft_user_kind_idx")]

    def __str__(self):
        return f"{self.get_kind_display()} · {self.title}"


class AIActionLog(models.Model):
    class Status(models.TextChoices):
        PROPOSED = "proposed", "À confirmer"
        EXECUTED = "executed", "Exécutée"
        REJECTED = "rejected", "Refusée"
        FAILED = "failed", "Échec"

    confirmation_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_actions")
    conversation = models.ForeignKey(AIConversation, on_delete=models.SET_NULL, null=True, blank=True, related_name="actions")
    message = models.ForeignKey(AIMessage, on_delete=models.SET_NULL, null=True, blank=True, related_name="action_logs")
    tool_name = models.CharField(max_length=80)
    label = models.CharField(max_length=220)
    request_payload = models.JSONField(default=dict)
    result_payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PROPOSED, db_index=True)
    error = models.CharField(max_length=1000, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    executed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status", "-created_at"], name="ai_action_user_status_idx"),
            models.Index(fields=["tool_name", "status", "-created_at"], name="ai_action_tool_status_idx"),
        ]

    def __str__(self):
        return f"{self.tool_name} · {self.user} · {self.status}"
