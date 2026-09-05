from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0009_resend_settings")]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("admin", "Administrateur"),
                    ("instructor", "Instructeur"),
                    ("student", "Étudiant"),
                    ("employer", "Entreprise / Recruteur"),
                ],
                default="student",
                max_length=20,
            ),
        ),
    ]
