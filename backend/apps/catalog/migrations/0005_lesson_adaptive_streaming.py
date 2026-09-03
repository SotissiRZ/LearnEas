from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0004_catalog_query_indexes"),
    ]

    operations = [
        migrations.AddField(
            model_name="lesson",
            name="hls_master_path",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="lesson",
            name="audio_hls_path",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="lesson",
            name="streaming_status",
            field=models.CharField(
                choices=[
                    ("pending", "En attente"),
                    ("processing", "Préparation en cours"),
                    ("ready", "Prêt"),
                    ("failed", "Échec"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="lesson",
            name="streaming_variants",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="lesson",
            name="streaming_error",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="lesson",
            name="streaming_updated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
