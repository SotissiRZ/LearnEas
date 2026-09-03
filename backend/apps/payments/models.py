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
                condition=models.Q(code__in=["stripe", "youcanpay", "geniuspay", "manual"]),
                name="pay_gateway_known_code",
            ),
        ]

    def clean(self):
        super().clean()
        self.code = (self.code or "").lower().strip()
        allowed = {"stripe", "youcanpay", "geniuspay", "manual"}
        if self.code not in allowed:
            raise ValidationError({"code": "Driver inconnu. Drivers disponibles : stripe, youcanpay, geniuspay, manual."})
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
        MANUAL = "manual", "Paiement manuel"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    provider = models.CharField(max_length=30, choices=Provider.choices, default=Provider.STRIPE)
    provider_sandbox = models.BooleanField(default=False, help_text="Environnement de paiement utilisé lors de la création de la commande.")
    base_total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="EUR")
    provider_reference = models.CharField(max_length=255, blank=True)
    invoice_number = models.CharField(max_length=50, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"], name="payments_or_status_6f471d_idx"),
            models.Index(fields=["user", "status"], name="payments_or_user_id_8d1a2e_idx"),
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

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    item_type = models.CharField(max_length=10, choices=ItemType.choices)
    course = models.ForeignKey("catalog.Course", on_delete=models.SET_NULL, null=True, blank=True)
    pdf_product = models.ForeignKey("catalog.PDFProduct", on_delete=models.SET_NULL, null=True, blank=True)
    formation = models.ForeignKey(
        "formations.InteractiveFormation", on_delete=models.SET_NULL, null=True, blank=True
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
        return f"{self.item_type} · {self.course or self.pdf_product or self.formation}"


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
