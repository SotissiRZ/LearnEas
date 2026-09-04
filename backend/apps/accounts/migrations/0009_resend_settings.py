from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0008_pricing_model")]
    operations = [
        migrations.AddField(model_name="platformsettings", name="resend_enabled", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="platformsettings", name="resend_from_name", field=models.CharField(default="KalanPro", max_length=120)),
        migrations.AddField(model_name="platformsettings", name="resend_from_email", field=models.EmailField(default="notifications@kalanpro.com", max_length=254)),
        migrations.AddField(model_name="platformsettings", name="resend_reply_to", field=models.EmailField(blank=True, default="support@kalanpro.com", max_length=254)),
    ]
