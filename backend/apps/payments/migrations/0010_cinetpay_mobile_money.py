from decimal import Decimal
from django.db import migrations, models


def seed_mobile_money(apps, schema_editor):
    Currency = apps.get_model("payments", "Currency")
    PaymentGateway = apps.get_model("payments", "PaymentGateway")

    # XOF/XAF sont arrimés à l'euro au taux fixe 1 EUR = 655,957 CFA.
    xof, _ = Currency.objects.get_or_create(
        code="XOF",
        defaults={
            "name": "Franc CFA BCEAO",
            "symbol": "F CFA",
            "exchange_rate": Decimal("655.95700000"),
            "decimal_places": 0,
            "is_active": True,
            "is_default": False,
            "sort_order": 30,
        },
    )
    xof.name = "Franc CFA BCEAO"
    xof.symbol = "F CFA"
    xof.exchange_rate = Decimal("655.95700000")
    xof.decimal_places = 0
    xof.is_active = True
    xof.is_default = False
    xof.sort_order = 30
    xof.save(update_fields=["name", "symbol", "exchange_rate", "decimal_places", "is_active", "is_default", "sort_order"])

    xaf, _ = Currency.objects.get_or_create(
        code="XAF",
        defaults={
            "name": "Franc CFA BEAC",
            "symbol": "F CFA",
            "exchange_rate": Decimal("655.95700000"),
            "decimal_places": 0,
            "is_active": True,
            "is_default": False,
            "sort_order": 40,
        },
    )
    xaf.name = "Franc CFA BEAC"
    xaf.symbol = "F CFA"
    xaf.exchange_rate = Decimal("655.95700000")
    xaf.decimal_places = 0
    xaf.is_active = True
    xaf.is_default = False
    xaf.sort_order = 40
    xaf.save(update_fields=["name", "symbol", "exchange_rate", "decimal_places", "is_active", "is_default", "sort_order"])

    gateway, _ = PaymentGateway.objects.get_or_create(
        code="cinetpay",
        defaults={
            "name": "CinetPay Mobile Money",
            "description": "Orange Money, MTN MoMo, Moov, Wave et autres wallets selon le pays",
            "is_active": False,
            "sandbox": False,
            "supported_currencies": ["XOF"],
            "sort_order": 15,
        },
    )
    supported = set(gateway.supported_currencies or [])
    supported.add("XOF")
    gateway.supported_currencies = sorted(supported)
    if not gateway.name:
        gateway.name = "CinetPay Mobile Money"
    if not gateway.description:
        gateway.description = "Orange Money, MTN MoMo, Moov, Wave et autres wallets selon le pays"
    gateway.save(update_fields=["name", "description", "supported_currencies"])


class Migration(migrations.Migration):
    dependencies = [("payments", "0009_eur_accounting_base")]

    operations = [
        migrations.RemoveConstraint(model_name="paymentgateway", name="pay_gateway_known_code"),
        migrations.AlterField(
            model_name="order",
            name="provider",
            field=models.CharField(
                choices=[
                    ("stripe", "Stripe"),
                    ("youcanpay", "YouCan Pay"),
                    ("geniuspay", "GeniusPay"),
                    ("cinetpay", "CinetPay Mobile Money"),
                    ("manual", "Paiement manuel"),
                ],
                default="stripe",
                max_length=30,
            ),
        ),
        migrations.RunPython(seed_mobile_money, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="paymentgateway",
            constraint=models.CheckConstraint(
                condition=models.Q(code__in=["stripe", "youcanpay", "geniuspay", "cinetpay", "manual"]),
                name="pay_gateway_known_code",
            ),
        ),
    ]
