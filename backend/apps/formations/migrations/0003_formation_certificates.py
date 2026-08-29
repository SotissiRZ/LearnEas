from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("formations", "0002_internal_live_sessions")]

    operations = [
        migrations.AddField(model_name="interactiveformation", name="certificate_enabled", field=models.BooleanField(default=True)),
        migrations.AddField(model_name="interactiveformation", name="certificate_auto_issue", field=models.BooleanField(default=True)),
        migrations.AddField(model_name="interactiveformation", name="certificate_attendance_percent", field=models.PositiveSmallIntegerField(default=80)),
        migrations.AddField(model_name="interactiveformation", name="certificate_validity_months", field=models.PositiveIntegerField(blank=True, null=True)),
        migrations.AddField(model_name="interactiveformation", name="certificate_title", field=models.CharField(default="Certificat de participation", max_length=180)),
        migrations.AddField(model_name="interactiveformation", name="certificate_subtitle", field=models.CharField(blank=True, max_length=220)),
        migrations.AddField(model_name="interactiveformation", name="certificate_description", field=models.TextField(blank=True)),
        migrations.AddField(model_name="interactiveformation", name="certificate_signatory_name", field=models.CharField(blank=True, max_length=180)),
        migrations.AddField(model_name="interactiveformation", name="certificate_signatory_title", field=models.CharField(blank=True, max_length=180)),
        migrations.AddField(model_name="interactiveformation", name="certificate_accent_color", field=models.CharField(default="#1f6f5c", max_length=20)),
        migrations.AddField(model_name="interactiveformation", name="certificate_number_prefix", field=models.CharField(default="LE-LIVE", max_length=30)),
        migrations.AddField(model_name="interactiveformation", name="certificate_show_duration", field=models.BooleanField(default=True)),
        migrations.AddField(model_name="interactiveformation", name="certificate_show_instructor", field=models.BooleanField(default=True)),
        migrations.AddField(model_name="interactiveformation", name="certificate_show_completion_date", field=models.BooleanField(default=True)),
    ]
