from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("assistant_ai", "0006_attachments"),
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
                    ("cv_improvement", "Amélioration CV"),
                    ("cover_letter", "Lettre de motivation"),
                    ("learning_gap_plan", "Plan de compétences"),
                    ("interview_prep", "Préparation entretien"),
                    ("interview_score", "Score de préparation entretien"),
                    ("interview_followup", "Suivi post-entretien"),
                    ("recruiter_scorecard", "Scorecard entretien recruteur"),
                ],
                max_length=30,
            ),
        ),
    ]
