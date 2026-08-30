from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("formations", "0005_live_room_collaboration"),
    ]

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
                ],
                max_length=10,
            ),
        ),
    ]
