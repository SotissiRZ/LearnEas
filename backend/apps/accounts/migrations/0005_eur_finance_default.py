from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0004_legal_certificate_settings")]

    operations = [
        migrations.AlterField(
            model_name="platformsettings",
            name="minimum_payout_amount",
            field=models.DecimalField(decimal_places=2, default=10, max_digits=10),
        ),
    ]
