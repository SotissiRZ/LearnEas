from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("catalog", "0007_lesson_offline_completion_controls")]

    operations = [
        migrations.AddField(
            model_name="course",
            name="premium_included",
            field=models.BooleanField(db_index=True, default=False, help_text="Inclus dans le catalogue KalanPro Premium lorsqu’un pass apprenant est actif."),
        ),
        migrations.AddField(
            model_name="pdfproduct",
            name="premium_included",
            field=models.BooleanField(db_index=True, default=False, help_text="Inclus dans le catalogue KalanPro Premium lorsqu’un pass apprenant est actif."),
        ),
    ]
