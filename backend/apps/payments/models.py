from django.conf import settings
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone


class Currency(models.Model):
    code = models.CharField(max_length=3, unique=True)
    name = models.CharField(max_length=80)
    symbol = models.CharField(max_length=12, blank=True)
    exchange_rate = models.DecimalField(max_digits=18, decimal_places=8, default=1, help_text="Valeur de 1 EUR exprimée dans cette devise (EUR est la devise comptable de base).")
    decimal_places = models.PositiveSmallIntegerField(default=2)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "code"]
        constraints = [
            models.UniqueConstraint(fields=["is_default"], condition=models.Q(is_default=True), name="uniq_default_currency"),
            models.CheckConstraint(condition=models.Q(exchange_rate__gt=0), name="curr_rate_gt_zero"),
            models.CheckConstraint(condition=models.Q(decimal_places__lte=2), name="curr_dec_places_lte2"),
            models.CheckConstraint(condition=models.Q(is_default=False) | models.Q(is_active=True), name="curr_default_active"),
            models.CheckConstraint(
                condition=~models.Q(code="EUR") | (models.Q(exchange_rate=1) & models.Q(is_active=True)),
                name="curr_eur_base_fixed",
            ),
        ]

    def clean(self):
        super().clean()
        self.code = (self.code or "").upper().strip()
        if len(self.code) != 3 or not self.code.isalpha():
            raise ValidationError({"code": "Utilisez un code ISO-4217 à 3 lettres."})
        if self.exchange_rate is None or self.exchange_rate <= 0:
            raise ValidationError({"exchange_rate": "Le taux doit être strictement positif."})
        if self.decimal_places is None or not 0 <= int(self.decimal_places) <= 2:
            raise ValidationError({"decimal_places": "Le nombre de décimales doit être compris entre 0 et 2."})
        if self.code == "EUR":
            self.exchange_rate = 1
            self.is_active = True
        if self.is_default:
            self.is_active = True

    def save(self, *args, **kwargs):
        self.code = self.code.upper().strip()
        if self.code == "EUR":
            self.exchange_rate = 1
            self.is_active = True
        # L'unicité de la devise d'affichage par défaut implique une mise à jour de deux
        # lignes. L'atomicité évite de laisser la plateforme sans défaut si le save échoue.
        with transaction.atomic():
            if self.is_default:
                Currency.objects.exclude(pk=self.pk).update(is_default=False)
                self.is_active = True
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.name}"


class PaymentGateway(models.Model):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=False)
    sandbox = models.BooleanField(default=True)
    supported_currencies = models.JSONField(default=list, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(code__in=["stripe", "youcanpay", "geniuspay", "cinetpay", "manual"]),
                name="pay_gateway_known_code",
            ),
        ]

    def clean(self):
        super().clean()
        self.code = (self.code or "").lower().strip()
        allowed = {"stripe", "youcanpay", "geniuspay", "cinetpay", "manual"}
        if self.code not in allowed:
            raise ValidationError({"code": "Driver inconnu. Drivers disponibles : stripe, youcanpay, geniuspay, cinetpay, manual."})
        codes = sorted({str(code).strip().upper() for code in (self.supported_currencies or []) if str(code).strip()})
        invalid = [code for code in codes if len(code) != 3 or not code.isalpha()]
        if invalid:
            raise ValidationError({"supported_currencies": f"Codes de devise invalides : {', '.join(invalid)}"})
        if codes:
            existing = set(Currency.objects.filter(code__in=codes).values_list("code", flat=True))
            missing = [code for code in codes if code not in existing]
            if missing:
                raise ValidationError({"supported_currencies": f"Ajoutez d'abord les devises suivantes : {', '.join(missing)}"})
        self.supported_currencies = codes

    def save(self, *args, **kwargs):
        self.code = self.code.lower().strip()
        self.supported_currencies = sorted({str(code).upper() for code in (self.supported_currencies or []) if str(code).strip()})
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        PAID = "paid", "Payée"
        FAILED = "failed", "Échouée"
        REFUNDED = "refunded", "Remboursée"

    class Provider(models.TextChoices):
        STRIPE = "stripe", "Stripe"
        YOUCANPAY = "youcanpay", "YouCan Pay"
        GENIUSPAY = "geniuspay", "GeniusPay"
        CINETPAY = "cinetpay", "CinetPay Mobile Money"
        MANUAL = "manual", "Paiement manuel"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    provider = models.CharField(max_length=30, choices=Provider.choices, default=Provider.STRIPE)
    provider_sandbox = models.BooleanField(default=False, help_text="Environnement de paiement utilisé lors de la création de la commande.")
    base_total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="EUR")
    provider_reference = models.CharField(max_length=255, blank=True)
    provider_status = models.CharField(max_length=80, blank=True)
    payment_method = models.CharField(max_length=80, blank=True)
    last_provider_check_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    checkout_url = models.TextField(blank=True)
    idempotency_key = models.CharField(max_length=128, blank=True)
    request_fingerprint = models.CharField(max_length=64, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    refund_reference = models.CharField(max_length=255, blank=True)
    refund_reason = models.CharField(max_length=500, blank=True)
    invoice_number = models.CharField(max_length=50, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"], name="payments_or_status_6f471d_idx"),
            models.Index(fields=["user", "status"], name="payments_or_user_id_8d1a2e_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "idempotency_key"],
                condition=~models.Q(idempotency_key=""),
                name="uniq_order_user_idempotency",
            ),
        ]

    def __str__(self):
        return f"Commande #{self.id} · {self.user} · {self.get_status_display()}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            import uuid
            self.invoice_number = f"LE-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    class ItemType(models.TextChoices):
        COURSE = "course", "Cours"
        PDF = "pdf", "PDF"
        FORMATION = "formation", "Formation interactive"
        MENTORING = "mentoring", "Mentorat"
        MENTOR_PACK = "mentor_pack", "Pack mentorat"
        EMPLOYER = "employer", "Droit recruteur"
        LEARNER_SUBSCRIPTION = "learner_subscription", "Abonnement apprenant"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    item_type = models.CharField(max_length=20, choices=ItemType.choices)
    course = models.ForeignKey("catalog.Course", on_delete=models.SET_NULL, null=True, blank=True)
    pdf_product = models.ForeignKey("catalog.PDFProduct", on_delete=models.SET_NULL, null=True, blank=True)
    formation = models.ForeignKey(
        "formations.InteractiveFormation", on_delete=models.SET_NULL, null=True, blank=True
    )
    mentorship_booking = models.ForeignKey(
        "formations.MentorshipBooking", on_delete=models.PROTECT, null=True, blank=True,
        related_name="order_items",
    )
    mentorship_pack = models.ForeignKey(
        "formations.MentorshipPack", on_delete=models.PROTECT, null=True, blank=True,
        related_name="order_items",
    )
    entitlement_code = models.CharField(
        max_length=191, blank=True,
        help_text="Produit/droit employeur ou futur identifiant d'entitlement lié à cette ligne de commande.",
    )
    # Snapshot du vendeur au moment de l'achat : indispensable pour que l'historique financier
    # reste correct même si le contenu change plus tard.
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sold_order_items",
    )
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    platform_fee_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    instructor_earning_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.item_type} · {self.course or self.pdf_product or self.formation or self.mentorship_booking or self.mentorship_pack or self.entitlement_code}"


class ActiveLearnerSubscriptionManager(models.Manager):
    def get_queryset(self):
        now = timezone.now()
        return super().get_queryset().filter(revoked_at__isnull=True, starts_at__lte=now, ends_at__gt=now)


class LearnerSubscription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="learner_subscriptions")
    source_order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name="learner_subscription")
    starts_at = models.DateTimeField(db_index=True)
    ends_at = models.DateTimeField(db_index=True)
    revoked_at = models.DateTimeField(null=True, blank=True, db_index=True)
    revocation_reason = models.CharField(max_length=500, blank=True)
    revenue_settled_at = models.DateTimeField(null=True, blank=True, db_index=True)
    creator_pool_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    platform_revenue_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ActiveLearnerSubscriptionManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["-starts_at", "-id"]
        indexes = [models.Index(fields=["user", "ends_at"], name="pay_learnsub_user_end_idx")]

    @property
    def is_active(self):
        now = timezone.now()
        return self.revoked_at is None and self.starts_at <= now < self.ends_at

    def __str__(self):
        return f"Premium {self.user} · {self.starts_at:%Y-%m-%d} → {self.ends_at:%Y-%m-%d}"


class PremiumRenewalProfile(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Planifié"
        ACTION_REQUIRED = "action_required", "Action requise"
        PAST_DUE = "past_due", "Échu"
        PAUSED = "paused", "En pause"
        CANCELLED = "cancelled", "Annulé"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="premium_renewal_profile"
    )
    enabled = models.BooleanField(default=False)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PAUSED, db_index=True)
    provider = models.CharField(max_length=30, choices=Order.Provider.choices, default=Order.Provider.STRIPE)
    currency = models.CharField(max_length=3, default="EUR")
    next_renewal_at = models.DateTimeField(null=True, blank=True, db_index=True)
    grace_ends_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    last_order = models.ForeignKey(
        Order, on_delete=models.SET_NULL, null=True, blank=True, related_name="premium_renewal_profiles"
    )
    failure_count = models.PositiveSmallIntegerField(default=0)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["enabled", "next_renewal_at"], name="pay_premrenew_due_idx")]

    def save(self, *args, **kwargs):
        self.currency = str(self.currency or "EUR").upper().strip()[:3]
        if not self.enabled and self.status == self.Status.SCHEDULED:
            self.status = self.Status.PAUSED
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Premium renewal {self.user} · {self.status}"


class PremiumContentUsage(models.Model):
    subscription = models.ForeignKey(
        LearnerSubscription, on_delete=models.PROTECT, related_name="content_usage"
    )
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="premium_content_usage"
    )
    course = models.ForeignKey(
        "catalog.Course", on_delete=models.SET_NULL, null=True, blank=True, related_name="premium_usage"
    )
    pdf_product = models.ForeignKey(
        "catalog.PDFProduct", on_delete=models.SET_NULL, null=True, blank=True, related_name="premium_usage"
    )
    interaction_count = models.PositiveIntegerField(default=0)
    watched_seconds = models.PositiveIntegerField(default=0)
    first_used_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(course__isnull=False, pdf_product__isnull=True)
                    | models.Q(course__isnull=True, pdf_product__isnull=False)
                ),
                name="prem_usage_one_content",
            ),
            models.UniqueConstraint(
                fields=["subscription", "course"], condition=models.Q(course__isnull=False),
                name="uniq_prem_usage_course",
            ),
            models.UniqueConstraint(
                fields=["subscription", "pdf_product"], condition=models.Q(pdf_product__isnull=False),
                name="uniq_prem_usage_pdf",
            ),
        ]
        indexes = [models.Index(fields=["subscription", "instructor"], name="pay_premusage_instr_idx")]


class PremiumRevenueAllocation(models.Model):
    subscription = models.ForeignKey(
        LearnerSubscription, on_delete=models.PROTECT, related_name="revenue_allocations"
    )
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="premium_revenue_allocations"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    usage_weight = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    creator_pool_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reversed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["subscription", "instructor"], name="uniq_prem_alloc_instr"),
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="prem_alloc_amount_gt_zero"),
        ]
        indexes = [models.Index(fields=["instructor", "created_at"], name="pay_premalloc_instr_idx")]

    def __str__(self):
        return f"Premium {self.subscription_id} → {self.instructor} · {self.amount} EUR"


class FormationSeatReservation(models.Model):
    """Réservation temporaire d'une place pendant un checkout externe.

    La ligne de formation est verrouillée pendant la création du checkout ; les réservations
    actives sont comptées avec les inscriptions afin d'éviter de vendre la dernière place
    à plusieurs utilisateurs en parallèle.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="seat_reservations")
    formation = models.ForeignKey(
        "formations.InteractiveFormation", on_delete=models.CASCADE, related_name="seat_reservations"
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="formation_seat_reservations")
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["order", "formation"], name="uniq_order_form_res"),
        ]
        indexes = [
            models.Index(fields=["formation", "expires_at"], name="payments_fo_formati_7a9c55_idx"),
            models.Index(fields=["user", "expires_at"], name="payments_fo_user_id_0cb3d6_idx"),
        ]

    @property
    def is_active(self):
        return self.expires_at > timezone.now() and self.order.status == Order.Status.PENDING

    def __str__(self):
        return f"Réservation {self.formation} · {self.user}"


class PayoutProfile(models.Model):
    class Method(models.TextChoices):
        BANK = "bank", "Virement bancaire"
        MOBILE_MONEY = "mobile_money", "Mobile Money"
        PAYPAL = "paypal", "PayPal"

    instructor = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payout_profile"
    )
    method = models.CharField(max_length=20, choices=Method.choices, default=Method.BANK)
    account_name = models.CharField(max_length=150, blank=True)
    account_reference = models.CharField(
        max_length=255, blank=True,
        help_text="IBAN/RIB, numéro Mobile Money ou email PayPal selon la méthode.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Paiement {self.instructor} · {self.get_method_display()}"


class InstructorPayout(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Demandé"
        PROCESSING = "processing", "En traitement"
        PAID = "paid", "Payé"
        FAILED = "failed", "Échoué"
        CANCELLED = "cancelled", "Annulé"

    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payouts"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    method = models.CharField(max_length=20, choices=PayoutProfile.Method.choices)
    account_reference_snapshot = models.CharField(max_length=255, blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    reference = models.CharField(max_length=120, blank=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["-requested_at"]

    def __str__(self):
        return f"{self.instructor} · {self.amount} EUR · {self.status}"


class InstructorLedgerEntry(models.Model):
    """Journal financier immuable des montants dus aux instructeurs.

    `amount` est signé : vente positive, remboursement/versement négatif.
    """
    class EntryType(models.TextChoices):
        SALE = "sale", "Vente"
        REFUND = "refund", "Remboursement"
        PAYOUT = "payout", "Versement"
        ADJUSTMENT = "adjustment", "Ajustement"
        PREMIUM = "premium", "Part Premium"
        PREMIUM_REFUND = "premium_refund", "Reprise Premium"

    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ledger_entries"
    )
    entry_type = models.CharField(max_length=20, choices=EntryType.choices, db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    order_item = models.ForeignKey(
        OrderItem, on_delete=models.SET_NULL, null=True, blank=True, related_name="ledger_entries"
    )
    payout = models.ForeignKey(
        InstructorPayout, on_delete=models.SET_NULL, null=True, blank=True, related_name="ledger_entries"
    )
    premium_allocation = models.ForeignKey(
        PremiumRevenueAllocation, on_delete=models.SET_NULL, null=True, blank=True, related_name="ledger_entries"
    )
    reference = models.CharField(max_length=160, blank=True)
    note = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["instructor", "created_at"], name="ledger_instr_created_idx"),
            models.Index(fields=["entry_type", "created_at"], name="ledger_type_created_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=~models.Q(amount=0), name="ledger_amount_nonzero"),
            models.UniqueConstraint(
                fields=["order_item", "entry_type"],
                condition=models.Q(order_item__isnull=False, entry_type__in=["sale", "refund"]),
                name="uniq_ledger_item_type",
            ),
            models.UniqueConstraint(
                fields=["payout", "entry_type"],
                condition=models.Q(payout__isnull=False, entry_type="payout"),
                name="uniq_ledger_payout",
            ),
            models.UniqueConstraint(
                fields=["premium_allocation", "entry_type"],
                condition=models.Q(
                    premium_allocation__isnull=False, entry_type__in=["premium", "premium_refund"]
                ),
                name="uniq_ledger_premium_alloc_type",
            ),
        ]

    def __str__(self):
        return f"{self.instructor} · {self.entry_type} · {self.amount}"

class PaymentAttempt(models.Model):
    """Tentative de paiement associée à une commande.

    Une commande reste la source de vérité métier; ce journal conserve l'historique
    opérationnel du prestataire sans exposer de données sensibles de paiement.
    """
    class Status(models.TextChoices):
        CREATED = "created", "Créée"
        REDIRECTED = "redirected", "Redirection créée"
        PENDING = "pending", "En attente"
        CHECKED = "checked", "Vérifiée"
        PAID = "paid", "Payée"
        FAILED = "failed", "Échouée"
        ERROR = "error", "Erreur prestataire"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payment_attempts")
    attempt_number = models.PositiveIntegerField(default=1)
    provider = models.CharField(max_length=30)
    provider_sandbox = models.BooleanField(default=False)
    provider_reference = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CREATED, db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3)
    provider_status = models.CharField(max_length=80, blank=True)
    payment_method = models.CharField(max_length=80, blank=True)
    check_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    last_error = models.CharField(max_length=500, blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["order", "attempt_number"], name="uniq_payment_attempt_no"),
        ]
        indexes = [
            models.Index(fields=["provider", "status", "started_at"], name="pay_attempt_provider_idx"),
            models.Index(fields=["order", "status"], name="pay_attempt_order_idx"),
        ]

    def __str__(self):
        return f"{self.order.invoice_number} · tentative {self.attempt_number} · {self.status}"


class PaymentEvent(models.Model):
    """Journal d'événements de paiement, volontairement redacted et append-only."""
    class Source(models.TextChoices):
        CHECKOUT = "checkout", "Checkout"
        WEBHOOK = "webhook", "Webhook"
        CONFIRM = "confirm", "Vérification utilisateur"
        RECONCILIATION = "reconciliation", "Réconciliation"
        ADMIN = "admin", "Administration"
        SYSTEM = "system", "Système"

    class Outcome(models.TextChoices):
        RECEIVED = "received", "Reçu"
        ACCEPTED = "accepted", "Accepté"
        IGNORED = "ignored", "Ignoré"
        REJECTED = "rejected", "Rejeté"
        ERROR = "error", "Erreur"

    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name="payment_events")
    provider = models.CharField(max_length=30, blank=True)
    provider_sandbox = models.BooleanField(default=False)
    source = models.CharField(max_length=20, choices=Source.choices)
    event_type = models.CharField(max_length=100, db_index=True)
    external_id = models.CharField(max_length=191, blank=True)
    outcome = models.CharField(max_length=20, choices=Outcome.choices, default=Outcome.RECEIVED, db_index=True)
    payload_hash = models.CharField(max_length=64, blank=True, db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    request_id = models.CharField(max_length=100, blank=True, db_index=True)
    message = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_sandbox", "external_id"],
                condition=~models.Q(external_id=""),
                name="uniq_payment_external_event",
            ),
        ]
        indexes = [
            models.Index(fields=["order", "created_at"], name="pay_event_order_created_idx"),
            models.Index(fields=["provider", "source", "created_at"], name="pay_event_provider_src_idx"),
        ]

    def __str__(self):
        return f"{self.provider or 'internal'} · {self.event_type} · {self.outcome}"


class PaymentIssue(models.Model):
    """Anomalie financière nécessitant une investigation humaine ou automatique."""
    class IssueType(models.TextChoices):
        AMOUNT_MISMATCH = "amount_mismatch", "Montant incohérent"
        CURRENCY_MISMATCH = "currency_mismatch", "Devise incohérente"
        PROVIDER_ERROR = "provider_error", "Erreur prestataire répétée"
        REFERENCE_MISMATCH = "reference_mismatch", "Référence incohérente"
        STALE_PENDING = "stale_pending", "Paiement en attente trop longtemps"
        WEBHOOK_REJECTED = "webhook_rejected", "Webhook rejeté"

    class Severity(models.TextChoices):
        WARNING = "warning", "Avertissement"
        CRITICAL = "critical", "Critique"

    class Status(models.TextChoices):
        OPEN = "open", "Ouverte"
        RESOLVED = "resolved", "Résolue"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payment_issues")
    issue_type = models.CharField(max_length=40, choices=IssueType.choices, db_index=True)
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.WARNING)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN, db_index=True)
    message = models.CharField(max_length=500)
    expected = models.JSONField(default=dict, blank=True)
    observed = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["order", "issue_type"],
                condition=models.Q(status="open"),
                name="uniq_open_payment_issue",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "severity", "created_at"], name="pay_issue_status_idx"),
        ]

    def resolve(self, note: str = ""):
        if self.status == self.Status.RESOLVED:
            return
        self.status = self.Status.RESOLVED
        self.resolved_at = timezone.now()
        self.resolution_note = str(note or "")[:500]
        self.save(update_fields=["status", "resolved_at", "resolution_note"])

    def __str__(self):
        return f"{self.order.invoice_number} · {self.issue_type} · {self.status}"
