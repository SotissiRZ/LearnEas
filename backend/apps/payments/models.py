from django.conf import settings
from django.db import models


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        PAID = "paid", "Payée"
        FAILED = "failed", "Échouée"
        REFUNDED = "refunded", "Remboursée"

    class Provider(models.TextChoices):
        STRIPE = "stripe", "Carte bancaire (Stripe)"
        PAYPAL = "paypal", "PayPal"
        MOBILE_MONEY = "mobile_money", "Mobile Money (Orange Money, MTN, Wave, M-Pesa...)"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    provider = models.CharField(max_length=20, choices=Provider.choices, default=Provider.STRIPE)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    provider_reference = models.CharField(max_length=255, blank=True)
    invoice_number = models.CharField(max_length=50, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Commande #{self.id} — {self.user} — {self.get_status_display()}"

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
        return f"{self.item_type} — {self.course or self.pdf_product or self.formation}"


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
        return f"Paiement {self.instructor} — {self.get_method_display()}"


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
        return f"{self.instructor} — {self.amount} MAD — {self.status}"
