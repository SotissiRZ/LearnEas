from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("assistant_ai", "0003_phase2_tools"),
    ]

    operations = [
        migrations.AlterField(
            model_name="aidraft",
            name="kind",
            field=models.CharField(
                choices=[
                    ("quiz", "Quiz"),
                    ("course_outline", "Plan de cours"),
                    ("mentor_plan", "Plan de mentorat"),
                    ("interview_rubric", "Grille d’entretien"),
                ],
                max_length=30,
            ),
        ),
    ]
