from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0012_learner_premium_pricing")]

    operations = [
        migrations.AddField(
            model_name="platformsettings",
            name="learner_premium_creator_pool_percent",
            field=models.PositiveSmallIntegerField(
                default=60,
                help_text="Part du revenu Premium distribuée aux créateurs selon l’usage éligible de la période.",
            ),
        ),
    ]
