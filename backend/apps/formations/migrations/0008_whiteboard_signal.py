from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("formations", "0007_session_email_invites")]

    operations = [
        migrations.AlterField(
            model_name="formationsignal",
            name="kind",
            field=models.CharField(
                choices=[
                    ("offer", "Offer"),
                    ("answer", "Answer"),
                    ("ice", "ICE candidate"),
                    ("chat", "Chat"),
                    ("control", "Moderation control"),
                    ("code", "Shared code editor"),
                    ("whiteboard", "Shared whiteboard"),
                ],
                max_length=10,
            ),
        ),
    ]
