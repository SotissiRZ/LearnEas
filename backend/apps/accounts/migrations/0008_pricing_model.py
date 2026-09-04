from decimal import Decimal
from django.db import migrations, models


def copy_existing_commission_to_mentor(apps, schema_editor):
    PlatformSettings = apps.get_model("accounts", "PlatformSettings")
    for config in PlatformSettings.objects.all():
        config.mentor_commission_percent = config.platform_commission_percent
        config.save(update_fields=["mentor_commission_percent"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [("accounts", "0007_kalanpro_branding")]

    operations = [
        migrations.AddField(
            model_name="platformsettings",
            name="pricing_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="platformsettings",
            name="instructor_pro_monthly_eur",
            field=models.DecimalField(decimal_places=2, default=Decimal("15.09"), max_digits=10),
        ),
        migrations.AddField(
            model_name="platformsettings",
            name="instructor_pro_commission_percent",
            field=models.PositiveSmallIntegerField(default=8),
        ),
        migrations.AddField(
            model_name="platformsettings",
            name="mentor_commission_percent",
            field=models.PositiveSmallIntegerField(default=15),
        ),
        migrations.AddField(
            model_name="platformsettings",
            name="employer_free_active_jobs",
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="platformsettings",
            name="employer_single_post_eur",
            field=models.DecimalField(decimal_places=2, default=Decimal("11.43"), max_digits=10),
        ),
        migrations.AddField(
            model_name="platformsettings",
            name="employer_pro_monthly_eur",
            field=models.DecimalField(decimal_places=2, default=Decimal("30.34"), max_digits=10),
        ),
        migrations.AddField(
            model_name="platformsettings",
            name="employer_pro_active_jobs",
            field=models.PositiveSmallIntegerField(default=5),
        ),
        migrations.AddField(
            model_name="platformsettings",
            name="employer_business_monthly_eur",
            field=models.DecimalField(decimal_places=2, default=Decimal("76.07"), max_digits=10),
        ),
        migrations.AddField(
            model_name="platformsettings",
            name="employer_business_active_jobs",
            field=models.PositiveSmallIntegerField(default=20),
        ),
        migrations.RunPython(copy_existing_commission_to_mentor, noop_reverse),
    ]
