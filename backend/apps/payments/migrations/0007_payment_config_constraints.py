from decimal import Decimal

from django.db import migrations, models


def sanitize_payment_config(apps, schema_editor):
    Currency = apps.get_model("payments", "Currency")
    PaymentGateway = apps.get_model("payments", "PaymentGateway")

    # Les contraintes sont défensives : normaliser d'abord d'éventuelles données saisies
    # via une ancienne version ou directement en base.
    for currency in Currency.objects.all():
        currency.code = (currency.code or "").upper().strip()[:3]
        if not currency.code or len(currency.code) != 3 or not currency.code.isalpha():
            currency.is_active = False
            currency.is_default = False
        if currency.exchange_rate is None or currency.exchange_rate <= 0:
            currency.exchange_rate = Decimal("1")
        currency.decimal_places = min(max(int(currency.decimal_places or 0), 0), 2)
        if currency.code == "MAD":
            currency.exchange_rate = Decimal("1")
            currency.is_active = True
        if currency.is_default:
            currency.is_active = True
        currency.save(update_fields=["code", "exchange_rate", "decimal_places", "is_active", "is_default"])

    allowed = {"stripe", "youcanpay", "geniuspay", "manual"}
    for gateway in PaymentGateway.objects.all():
        gateway.code = (gateway.code or "").lower().strip()
        if gateway.code not in allowed:
            gateway.is_active = False
            # Une valeur invalide ne peut pas survivre à la future contrainte. Les lignes
            # inconnues sont supprimées car aucun driver exécutable ne leur correspond.
            gateway.delete()
            continue
        gateway.supported_currencies = sorted({
            str(code).strip().upper()
            for code in (gateway.supported_currencies or [])
            if isinstance(code, str) and len(code.strip()) == 3 and code.strip().isalpha()
        })
        gateway.save(update_fields=["code", "supported_currencies", "is_active"])


class Migration(migrations.Migration):
    dependencies = [("payments", "0006_order_provider_environment")]

    operations = [
        migrations.RunPython(sanitize_payment_config, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="currency",
            constraint=models.CheckConstraint(condition=models.Q(exchange_rate__gt=0), name="curr_rate_gt_zero"),
        ),
        migrations.AddConstraint(
            model_name="currency",
            constraint=models.CheckConstraint(condition=models.Q(decimal_places__lte=2), name="curr_dec_places_lte2"),
        ),
        migrations.AddConstraint(
            model_name="currency",
            constraint=models.CheckConstraint(condition=models.Q(is_default=False) | models.Q(is_active=True), name="curr_default_active"),
        ),
        migrations.AddConstraint(
            model_name="currency",
            constraint=models.CheckConstraint(
                condition=~models.Q(code="MAD") | (models.Q(exchange_rate=1) & models.Q(is_active=True)),
                name="curr_mad_base_fixed",
            ),
        ),
        migrations.AddConstraint(
            model_name="paymentgateway",
            constraint=models.CheckConstraint(
                condition=models.Q(code__in=["stripe", "youcanpay", "geniuspay", "manual"]),
                name="pay_gateway_known_code",
            ),
        ),
    ]
