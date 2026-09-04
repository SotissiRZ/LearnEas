from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("assistant_ai", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="aisettings",
            name="input_cost_per_million_eur",
            field=models.DecimalField(decimal_places=4, default=0, help_text="Coût estimé du modèle pour 1M tokens d'entrée.", max_digits=10),
        ),
        migrations.AddField(
            model_name="aisettings",
            name="output_cost_per_million_eur",
            field=models.DecimalField(decimal_places=4, default=0, help_text="Coût estimé du modèle pour 1M tokens de sortie.", max_digits=10),
        ),
        migrations.AddField(
            model_name="aimessage",
            name="feedback",
            field=models.CharField(blank=True, choices=[("helpful", "Utile"), ("unhelpful", "À améliorer")], max_length=20),
        ),
        migrations.AddField(
            model_name="aimessage",
            name="feedback_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="aimessage",
            name="feedback_comment",
            field=models.CharField(blank=True, max_length=1000),
        ),
        migrations.AddField(
            model_name="aiusage",
            name="estimated_cost_eur",
            field=models.DecimalField(decimal_places=6, default=0, max_digits=12),
        ),
        migrations.CreateModel(
            name="AIEvaluationCase",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("question", models.CharField(max_length=500)),
                ("expected_source_type", models.CharField(choices=[("course", "Cours"), ("lesson", "Leçon / transcript"), ("pdf_resource", "PDF de cours"), ("pdf_product", "PDF autonome")], max_length=30)),
                ("expected_source_id", models.PositiveIntegerField()),
                ("enabled", models.BooleanField(default=True)),
                ("notes", models.CharField(blank=True, max_length=500)),
                ("last_passed", models.BooleanField(blank=True, null=True)),
                ("last_rank", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("last_run_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["id"]},
        ),
        migrations.AddConstraint(
            model_name="aievaluationcase",
            constraint=models.UniqueConstraint(fields=("question", "expected_source_type", "expected_source_id"), name="uniq_ai_eval_case"),
        ),
    ]
