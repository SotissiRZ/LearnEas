from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0006_domain_category_domain"),
    ]

    operations = [
        migrations.AddField(
            model_name="course",
            name="video_completion_threshold_percent",
            field=models.PositiveSmallIntegerField(
                default=90,
                validators=[MinValueValidator(50), MaxValueValidator(100)],
            ),
        ),
        migrations.AddField(
            model_name="lesson",
            name="duration_seconds",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="lesson",
            name="offline_download_allowed",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="lesson",
            name="offline_video_path",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="lesson",
            name="offline_video_size_bytes",
            field=models.PositiveBigIntegerField(default=0),
        ),
    ]
