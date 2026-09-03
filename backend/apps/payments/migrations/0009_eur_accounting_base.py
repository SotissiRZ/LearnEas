from decimal import Decimal, ROUND_HALF_UP

from django.db import migrations, models


CENT = Decimal("0.01")
FALLBACK_EUR_PER_MAD = Decimal("0.09200000")


def _money(value, factor):
    return (Decimal(value or 0) * factor).quantize(CENT, rounding=ROUND_HALF_UP)


def switch_to_eur_base(apps, schema_editor):
    Currency = apps.get_model("payments", "Currency")
    PaymentGateway = apps.get_model("payments", "PaymentGateway")
    Order = apps.get_model("payments", "Order")
    OrderItem = apps.get_model("payments", "OrderItem")
    InstructorPayout = apps.get_model("payments", "InstructorPayout")
    Course = apps.get_model("catalog", "Course")
    PDFProduct = apps.get_model("catalog", "PDFProduct")
    InteractiveFormation = apps.get_model("formations", "InteractiveFormation")
    PlatformSettings = apps.get_model("accounts", "PlatformSettings")

    eur = Currency.objects.filter(code="EUR").first()
    old_eur_rate = Decimal(eur.exchange_rate) if eur and eur.exchange_rate else FALLBACK_EUR_PER_MAD
    if old_eur_rate <= 0:
        old_eur_rate = FALLBACK_EUR_PER_MAD

    # Conserver la valeur économique des montants existants : ils étaient enregistrés en MAD
    # comptable. On les convertit une seule fois vers EUR avec le taux EUR/MAD déjà configuré.
    for course in Course.objects.all().only("id", "price", "discount_price"):
        course.price = _money(course.price, old_eur_rate)
        if course.discount_price is not None:
            course.discount_price = _money(course.discount_price, old_eur_rate)
        course.save(update_fields=["price", "discount_price"])

    for pdf in PDFProduct.objects.all().only("id", "price"):
        pdf.price = _money(pdf.price, old_eur_rate)
        pdf.save(update_fields=["price"])

    for formation in InteractiveFormation.objects.all().only("id", "price"):
        formation.price = _money(formation.price, old_eur_rate)
        formation.save(update_fields=["price"])

    for order in Order.objects.all().only("id", "base_total_amount"):
        order.base_total_amount = _money(order.base_total_amount, old_eur_rate)
        order.save(update_fields=["base_total_amount"])

    for item in OrderItem.objects.all().only(
        "id", "unit_price", "platform_fee_amount", "instructor_earning_amount"
    ):
        item.unit_price = _money(item.unit_price, old_eur_rate)
        item.platform_fee_amount = _money(item.platform_fee_amount, old_eur_rate)
        item.instructor_earning_amount = _money(item.instructor_earning_amount, old_eur_rate)
        item.save(update_fields=["unit_price", "platform_fee_amount", "instructor_earning_amount"])

    for payout in InstructorPayout.objects.all().only("id", "amount"):
        payout.amount = _money(payout.amount, old_eur_rate)
        payout.save(update_fields=["amount"])

    for config in PlatformSettings.objects.all().only("id", "minimum_payout_amount"):
        config.minimum_payout_amount = _money(config.minimum_payout_amount, old_eur_rate)
        config.save(update_fields=["minimum_payout_amount"])

    # Rebaser tous les taux : avant, ils exprimaient 1 MAD dans la devise cible ; désormais
    # ils expriment 1 EUR dans la devise cible. Ex.: MAD = 1 / (EUR par MAD).
    currencies = list(Currency.objects.all())
    Currency.objects.update(is_default=False)
    for currency in currencies:
        old_rate = Decimal(currency.exchange_rate or 1)
        currency.exchange_rate = (old_rate / old_eur_rate).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)
        if currency.code == "EUR":
            currency.exchange_rate = Decimal("1")
            currency.is_active = True
            currency.is_default = True
            currency.sort_order = 0
        else:
            currency.is_default = False
            if currency.code == "MAD" and currency.sort_order == 0:
                currency.sort_order = 10
        currency.save(update_fields=["exchange_rate", "is_active", "is_default", "sort_order"])

    eur, _ = Currency.objects.get_or_create(
        code="EUR",
        defaults={
            "name": "Euro",
            "symbol": "€",
            "exchange_rate": Decimal("1"),
            "decimal_places": 2,
            "is_active": True,
            "is_default": True,
            "sort_order": 0,
        },
    )
    eur.name = eur.name or "Euro"
    eur.symbol = eur.symbol or "€"
    eur.exchange_rate = Decimal("1")
    eur.decimal_places = 2
    eur.is_active = True
    eur.is_default = True
    eur.sort_order = 0
    eur.save(update_fields=["name", "symbol", "exchange_rate", "decimal_places", "is_active", "is_default", "sort_order"])

    # Le paiement manuel doit au minimum pouvoir traiter la devise comptable EUR.
    for gateway in PaymentGateway.objects.filter(code__in=["stripe", "manual"]):
        supported = list(gateway.supported_currencies or [])
        if supported and "EUR" not in supported:
            supported.append("EUR")
            gateway.supported_currencies = sorted(set(supported))
            gateway.save(update_fields=["supported_currencies"])


def restore_mad_base(apps, schema_editor):
    """Retour défensif pour rollback de développement.

    Il rebase les taux sur MAD et remet MAD comme devise par défaut. Les montants historiques ne
    sont pas reconvertis afin d'éviter une double transformation destructive lors d'allers-retours
    de migrations en environnement de développement.
    """
    Currency = apps.get_model("payments", "Currency")
    mad = Currency.objects.filter(code="MAD").first()
    if not mad:
        mad = Currency.objects.create(
            code="MAD", name="Dirham marocain", symbol="MAD", exchange_rate=Decimal("1"),
            decimal_places=2, is_active=True, is_default=False, sort_order=0,
        )
    mad_per_eur = Decimal(mad.exchange_rate or 1)
    if mad_per_eur <= 0:
        mad_per_eur = Decimal("10.86956522")
    Currency.objects.update(is_default=False)
    for currency in Currency.objects.all():
        currency.exchange_rate = (Decimal(currency.exchange_rate or 1) / mad_per_eur).quantize(
            Decimal("0.00000001"), rounding=ROUND_HALF_UP
        )
        if currency.code == "MAD":
            currency.exchange_rate = Decimal("1")
            currency.is_active = True
            currency.is_default = True
            currency.sort_order = 0
        currency.save(update_fields=["exchange_rate", "is_active", "is_default", "sort_order"])


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0008_rename_seat_reservation_constraint"),
        ("catalog", "0004_catalog_query_indexes"),
        ("formations", "0008_whiteboard_signal"),
        ("accounts", "0005_eur_finance_default"),
    ]

    operations = [
        migrations.RemoveConstraint(model_name="currency", name="curr_mad_base_fixed"),
        migrations.AlterField(
            model_name="currency",
            name="exchange_rate",
            field=models.DecimalField(
                decimal_places=8,
                default=1,
                help_text="Valeur de 1 EUR exprimée dans cette devise (EUR est la devise comptable de base).",
                max_digits=18,
            ),
        ),
        migrations.AlterField(
            model_name="order",
            name="currency",
            field=models.CharField(default="EUR", max_length=3),
        ),
        migrations.RunPython(switch_to_eur_base, restore_mad_base),
        migrations.AddConstraint(
            model_name="currency",
            constraint=models.CheckConstraint(
                condition=~models.Q(code="EUR") | (models.Q(exchange_rate=1) & models.Q(is_active=True)),
                name="curr_eur_base_fixed",
            ),
        ),
    ]
