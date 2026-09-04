from django.db import migrations, models


def apply_kalanpro_brand(apps, schema_editor):
    PlatformSettings = apps.get_model("accounts", "PlatformSettings")
    User = apps.get_model("accounts", "User")

    settings = PlatformSettings.objects.filter(pk=1).first()
    if settings:
        changed = []
        if settings.site_name in {"LearnEas", ""}:
            settings.site_name = "KalanPro"; changed.append("site_name")
        if settings.legal_company_name in {"LearnEas", ""}:
            settings.legal_company_name = "KalanPro"; changed.append("legal_company_name")
        if settings.support_email == "support@learneas.com":
            settings.support_email = "support@kalanpro.com"; changed.append("support_email")
        if settings.privacy_email == "privacy@learneas.com":
            settings.privacy_email = "privacy@kalanpro.com"; changed.append("privacy_email")
        if settings.certificate_default_accent_color == "#1f6f5c":
            settings.certificate_default_accent_color = "#ff641a"; changed.append("certificate_default_accent_color")
        if settings.certificate_default_number_prefix == "LE-CERT":
            settings.certificate_default_number_prefix = "KP-CERT"; changed.append("certificate_default_number_prefix")
        whatsapp_names = {
            "whatsapp_payment_template_name": ("learneas_payment_confirmed", "kalanpro_payment_confirmed"),
            "whatsapp_live_template_name": ("learneas_live_reminder", "kalanpro_live_reminder"),
            "whatsapp_inactivity_template_name": ("learneas_inactivity_reminder", "kalanpro_inactivity_reminder"),
            "whatsapp_certificate_template_name": ("learneas_certificate_ready", "kalanpro_certificate_ready"),
        }
        for field, (old, new) in whatsapp_names.items():
            if getattr(settings, field) == old:
                setattr(settings, field, new); changed.append(field)
        if changed:
            settings.save(update_fields=changed + ["updated_at"])

    demo_emails = {
        "admin@learneas.com": "admin@kalanpro.com",
        "sarah@learneas.com": "sarah@kalanpro.com",
        "koffi@learneas.com": "koffi@kalanpro.com",
        "amina@learneas.com": "amina@kalanpro.com",
        "fatou@learneas.com": "fatou@kalanpro.com",
        "jean@learneas.com": "jean@kalanpro.com",
        "aicha@learneas.com": "aicha@kalanpro.com",
        "recruteur@learneas.com": "recruteur@kalanpro.com",
    }
    for old, new in demo_emails.items():
        if not User.objects.filter(email=new).exists():
            User.objects.filter(email=old).update(email=new)


class Migration(migrations.Migration):
    dependencies = [("accounts", "0006_whatsapp_platform_settings")]

    operations = [
        migrations.AlterField(
            model_name="platformsettings", name="site_name",
            field=models.CharField(default="KalanPro", max_length=120),
        ),
        migrations.AlterField(
            model_name="platformsettings", name="support_email",
            field=models.EmailField(default="support@kalanpro.com", max_length=254),
        ),
        migrations.AlterField(
            model_name="platformsettings", name="legal_company_name",
            field=models.CharField(blank=True, default="KalanPro", max_length=180),
        ),
        migrations.AlterField(
            model_name="platformsettings", name="privacy_email",
            field=models.EmailField(blank=True, default="privacy@kalanpro.com", max_length=254),
        ),
        migrations.AlterField(
            model_name="platformsettings", name="certificate_default_accent_color",
            field=models.CharField(default="#ff641a", max_length=20),
        ),
        migrations.AlterField(
            model_name="platformsettings", name="certificate_default_number_prefix",
            field=models.CharField(default="KP-CERT", max_length=30),
        ),
        migrations.AlterField(
            model_name="platformsettings", name="whatsapp_payment_template_name",
            field=models.CharField(default="kalanpro_payment_confirmed", max_length=120),
        ),
        migrations.AlterField(
            model_name="platformsettings", name="whatsapp_live_template_name",
            field=models.CharField(default="kalanpro_live_reminder", max_length=120),
        ),
        migrations.AlterField(
            model_name="platformsettings", name="whatsapp_inactivity_template_name",
            field=models.CharField(default="kalanpro_inactivity_reminder", max_length=120),
        ),
        migrations.AlterField(
            model_name="platformsettings", name="whatsapp_certificate_template_name",
            field=models.CharField(default="kalanpro_certificate_ready", max_length=120),
        ),
        migrations.RunPython(apply_kalanpro_brand, migrations.RunPython.noop),
    ]
