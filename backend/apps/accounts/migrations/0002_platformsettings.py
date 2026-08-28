from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="PlatformSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("site_name", models.CharField(default="LearnEas", max_length=120)),
                ("support_email", models.EmailField(default="support@learneas.com", max_length=254)),
                ("registration_enabled", models.BooleanField(default=True)),
                ("instructor_applications_enabled", models.BooleanField(default=True)),
                ("platform_commission_percent", models.PositiveSmallIntegerField(default=15)),
                ("minimum_payout_amount", models.DecimalField(decimal_places=2, default=100, max_digits=10)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Paramètres de la plateforme",
                "verbose_name_plural": "Paramètres de la plateforme",
            },
        ),
    ]
