from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("formations", "0010_revocable_entitlements"),
    ]

    operations = [
        migrations.RenameIndex(
            model_name="formationattendance",
            old_name="formations__session_727f67_idx",
            new_name="formations__session_c9693c_idx",
        ),
        migrations.RenameIndex(
            model_name="formationroomfile",
            old_name="formations_session_94ff2c_idx",
            new_name="formations__session_1e0653_idx",
        ),
        migrations.RenameIndex(
            model_name="formationsignal",
            old_name="formations__session_7c3f3c_idx",
            new_name="formations__session_525424_idx",
        ),
        migrations.AlterField(
            model_name="formationsession",
            name="meeting_link",
            field=models.URLField(blank=True, help_text="Champ historique · non utilisé par KalanPro"),
        ),
    ]
