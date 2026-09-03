from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0005_eur_finance_default")]

    operations = [
        migrations.AddField(model_name="platformsettings", name="whatsapp_enabled", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="platformsettings", name="whatsapp_template_language", field=models.CharField(default="fr", max_length=16)),
        migrations.AddField(model_name="platformsettings", name="whatsapp_payment_template_name", field=models.CharField(default="learneas_payment_confirmed", max_length=120)),
        migrations.AddField(model_name="platformsettings", name="whatsapp_live_template_name", field=models.CharField(default="learneas_live_reminder", max_length=120)),
        migrations.AddField(model_name="platformsettings", name="whatsapp_inactivity_template_name", field=models.CharField(default="learneas_inactivity_reminder", max_length=120)),
        migrations.AddField(model_name="platformsettings", name="whatsapp_certificate_template_name", field=models.CharField(default="learneas_certificate_ready", max_length=120)),
        migrations.AddField(model_name="platformsettings", name="whatsapp_test_template_name", field=models.CharField(default="hello_world", max_length=120)),
        migrations.AddField(model_name="platformsettings", name="whatsapp_live_reminder_minutes", field=models.PositiveSmallIntegerField(default=30)),
        migrations.AddField(model_name="platformsettings", name="whatsapp_inactivity_days", field=models.PositiveSmallIntegerField(default=4)),
    ]
