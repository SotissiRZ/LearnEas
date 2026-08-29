from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("catalog", "0002_pdfresource_cover_image")]

    operations = [
        migrations.AddField(model_name="course", name="certificate_enabled", field=models.BooleanField(default=True)),
        migrations.AddField(model_name="course", name="certificate_auto_issue", field=models.BooleanField(default=True)),
        migrations.AddField(model_name="course", name="certificate_threshold_percent", field=models.PositiveSmallIntegerField(default=100)),
        migrations.AddField(model_name="course", name="certificate_validity_months", field=models.PositiveIntegerField(blank=True, null=True)),
        migrations.AddField(model_name="course", name="certificate_title", field=models.CharField(default="Certificat de réussite", max_length=180)),
        migrations.AddField(model_name="course", name="certificate_subtitle", field=models.CharField(blank=True, max_length=220)),
        migrations.AddField(model_name="course", name="certificate_description", field=models.TextField(blank=True)),
        migrations.AddField(model_name="course", name="certificate_signatory_name", field=models.CharField(blank=True, max_length=180)),
        migrations.AddField(model_name="course", name="certificate_signatory_title", field=models.CharField(blank=True, max_length=180)),
        migrations.AddField(model_name="course", name="certificate_accent_color", field=models.CharField(default="#1f6f5c", max_length=20)),
        migrations.AddField(model_name="course", name="certificate_number_prefix", field=models.CharField(default="LE-CERT", max_length=30)),
        migrations.AddField(model_name="course", name="certificate_show_duration", field=models.BooleanField(default=True)),
        migrations.AddField(model_name="course", name="certificate_show_instructor", field=models.BooleanField(default=True)),
        migrations.AddField(model_name="course", name="certificate_show_completion_date", field=models.BooleanField(default=True)),
        migrations.AddField(model_name="lesson", name="subtitles_file", field=models.FileField(blank=True, help_text="Sous-titres WebVTT (.vtt)", null=True, upload_to="courses/subtitles/")),
        migrations.AddField(model_name="lesson", name="transcript", field=models.TextField(blank=True, help_text="Transcription texte de la leçon")),
    ]
