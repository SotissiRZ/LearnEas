from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0010_user_employer_role")]
    operations = [
        migrations.AddField(
            model_name="platformsettings",
            name="whatsapp_recruitment_template_name",
            field=models.CharField(default="kalanpro_recruitment_update", max_length=120),
        ),
    ]
