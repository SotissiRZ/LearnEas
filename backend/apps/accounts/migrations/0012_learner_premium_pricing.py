from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0011_whatsapp_recruitment_template")]

    operations = [
        migrations.AddField(
            model_name="platformsettings",
            name="learner_premium_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="platformsettings",
            name="learner_premium_monthly_eur",
            field=models.DecimalField(decimal_places=2, default=Decimal("9.99"), max_digits=10),
        ),
    ]
