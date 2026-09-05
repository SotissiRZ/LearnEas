from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("enrollments", "0006_revocable_entitlements_certificate_history")]

    operations = [
        migrations.AddField(
            model_name="lessonprogress",
            name="last_watch_heartbeat_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
