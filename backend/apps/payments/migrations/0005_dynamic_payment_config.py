from decimal import Decimal
from django.db import migrations, models


def seed_payment_config(apps, schema_editor):
    Currency = apps.get_model("payments", "Currency")
    Gateway = apps.get_model("payments", "PaymentGateway")
    Order = apps.get_model("payments", "Order")
    Currency.objects.get_or_create(code="MAD", defaults={"name": "Dirham marocain", "symbol": "MAD", "exchange_rate": Decimal("1"), "is_active": True, "is_default": True, "sort_order": 0})
    Currency.objects.get_or_create(code="EUR", defaults={"name": "Euro", "symbol": "€", "exchange_rate": Decimal("0.092"), "is_active": False, "sort_order": 10})
    Currency.objects.get_or_create(code="USD", defaults={"name": "Dollar américain", "symbol": "$", "exchange_rate": Decimal("0.100"), "is_active": False, "sort_order": 20})
    Currency.objects.get_or_create(code="XOF", defaults={"name": "Franc CFA BCEAO", "symbol": "FCFA", "exchange_rate": Decimal("60.3"), "is_active": False, "sort_order": 30})
    Gateway.objects.get_or_create(code="stripe", defaults={"name": "Stripe", "description": "Cartes bancaires via Stripe Checkout", "is_active": True, "sandbox": True, "supported_currencies": ["MAD", "EUR", "USD"], "sort_order": 0})
    Gateway.objects.get_or_create(code="youcanpay", defaults={"name": "YouCan Pay", "description": "Paiement marocain via facture hébergée YouCan Pay", "is_active": False, "sandbox": True, "supported_currencies": ["MAD"], "sort_order": 10})
    Gateway.objects.get_or_create(code="geniuspay", defaults={"name": "GeniusPay", "description": "Mobile money et cartes en Afrique", "is_active": False, "sandbox": True, "supported_currencies": ["XOF", "EUR", "USD"], "sort_order": 20})
    Gateway.objects.get_or_create(code="manual", defaults={"name": "Paiement manuel", "description": "Validation manuelle par un administrateur", "is_active": False, "sandbox": False, "supported_currencies": ["MAD"], "sort_order": 90})
    Order.objects.filter(base_total_amount=0).update(base_total_amount=models.F("total_amount"))


class Migration(migrations.Migration):
    dependencies = [("payments", "0004_seat_reservations_and_indexes")]
    operations = [
        migrations.CreateModel(
            name="Currency",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=3, unique=True)),
                ("name", models.CharField(max_length=80)),
                ("symbol", models.CharField(blank=True, max_length=12)),
                ("exchange_rate", models.DecimalField(decimal_places=8, default=1, help_text="Valeur de 1 MAD exprimée dans cette devise (MAD est la devise comptable de base).", max_digits=18)),
                ("decimal_places", models.PositiveSmallIntegerField(default=2)),
                ("is_active", models.BooleanField(default=True)),
                ("is_default", models.BooleanField(default=False)),
                ("sort_order", models.PositiveIntegerField(default=0)),
            ],
            options={"ordering": ["sort_order", "code"]},
        ),
        migrations.CreateModel(
            name="PaymentGateway",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=30, unique=True)),
                ("name", models.CharField(max_length=100)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("is_active", models.BooleanField(default=False)),
                ("sandbox", models.BooleanField(default=True)),
                ("supported_currencies", models.JSONField(blank=True, default=list)),
                ("sort_order", models.PositiveIntegerField(default=0)),
            ],
            options={"ordering": ["sort_order", "name"]},
        ),
        migrations.AddField(model_name="order", name="base_total_amount", field=models.DecimalField(decimal_places=2, default=0, max_digits=10)),
        migrations.AddField(model_name="order", name="currency", field=models.CharField(default="MAD", max_length=3)),
        migrations.AlterField(model_name="order", name="provider", field=models.CharField(choices=[("stripe", "Stripe"), ("youcanpay", "YouCan Pay"), ("geniuspay", "GeniusPay"), ("manual", "Paiement manuel")], default="stripe", max_length=30)),
        migrations.AddConstraint(model_name="currency", constraint=models.UniqueConstraint(fields=("is_default",), condition=models.Q(("is_default", True)), name="uniq_default_currency")),
        migrations.RunPython(seed_payment_config, migrations.RunPython.noop),
    ]
