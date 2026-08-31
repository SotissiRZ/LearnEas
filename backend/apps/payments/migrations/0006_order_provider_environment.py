from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("payments", "0005_dynamic_payment_config")]
    operations = [
        migrations.AddField(
            model_name="order",
            name="provider_sandbox",
            field=models.BooleanField(default=False, help_text="Environnement de paiement utilisé lors de la création de la commande."),
        ),
    ]
