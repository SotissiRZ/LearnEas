from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0003_instructorapplication")]

    operations = [
        migrations.AddField(model_name="platformsettings", name="legal_company_name", field=models.CharField(blank=True, default="LearnEas", max_length=180)),
        migrations.AddField(model_name="platformsettings", name="legal_address", field=models.TextField(blank=True)),
        migrations.AddField(model_name="platformsettings", name="legal_country", field=models.CharField(blank=True, default="Maroc", max_length=100)),
        migrations.AddField(model_name="platformsettings", name="legal_registration_number", field=models.CharField(blank=True, max_length=120)),
        migrations.AddField(model_name="platformsettings", name="legal_tax_number", field=models.CharField(blank=True, max_length=120)),
        migrations.AddField(model_name="platformsettings", name="privacy_email", field=models.EmailField(blank=True, default="privacy@learneas.com", max_length=254)),
        migrations.AddField(model_name="platformsettings", name="terms_updated_at", field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name="platformsettings", name="privacy_updated_at", field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name="platformsettings", name="refund_policy_days", field=models.PositiveSmallIntegerField(default=14)),
        migrations.AddField(model_name="platformsettings", name="certificate_verification_enabled", field=models.BooleanField(default=True)),
        migrations.AddField(model_name="platformsettings", name="certificate_default_enabled", field=models.BooleanField(default=True)),
        migrations.AddField(model_name="platformsettings", name="certificate_default_auto_issue", field=models.BooleanField(default=True)),
        migrations.AddField(model_name="platformsettings", name="certificate_default_threshold_percent", field=models.PositiveSmallIntegerField(default=100)),
        migrations.AddField(model_name="platformsettings", name="certificate_default_attendance_percent", field=models.PositiveSmallIntegerField(default=80)),
        migrations.AddField(model_name="platformsettings", name="certificate_default_validity_months", field=models.PositiveIntegerField(blank=True, null=True)),
        migrations.AddField(model_name="platformsettings", name="certificate_default_title", field=models.CharField(default="Certificat de réussite", max_length=180)),
        migrations.AddField(model_name="platformsettings", name="certificate_default_subtitle", field=models.CharField(blank=True, max_length=220)),
        migrations.AddField(model_name="platformsettings", name="certificate_default_signatory_name", field=models.CharField(blank=True, max_length=180)),
        migrations.AddField(model_name="platformsettings", name="certificate_default_signatory_title", field=models.CharField(blank=True, max_length=180)),
        migrations.AddField(model_name="platformsettings", name="certificate_default_accent_color", field=models.CharField(default="#1f6f5c", max_length=20)),
        migrations.AddField(model_name="platformsettings", name="certificate_default_number_prefix", field=models.CharField(default="LE-CERT", max_length=30)),
    ]
