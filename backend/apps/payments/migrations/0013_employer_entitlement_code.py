from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0012_payment_hardening_ledger"),
    ]

    operations = [
        migrations.AlterField(
            model_name="orderitem",
            name="item_type",
            field=models.CharField(
                choices=[
                    ("course", "Cours"),
                    ("pdf", "PDF"),
                    ("formation", "Formation interactive"),
                    ("mentoring", "Mentorat"),
                    ("employer", "Droit recruteur"),
                ],
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="entitlement_code",
            field=models.CharField(
                blank=True,
                help_text="Produit/droit employeur ou futur identifiant d'entitlement lié à cette ligne de commande.",
                max_length=191,
            ),
        ),
    ]
