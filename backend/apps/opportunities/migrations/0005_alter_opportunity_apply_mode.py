from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("opportunities", "0004_employer_governance"),
    ]

    operations = [
        migrations.AlterField(
            model_name="opportunity",
            name="apply_mode",
            field=models.CharField(
                choices=[
                    ("internal", "Candidature KalanPro"),
                    ("external", "Lien externe"),
                ],
                default="internal",
                max_length=20,
            ),
        ),
    ]
