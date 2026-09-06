from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("enrollments", "0007_lessonprogress_watch_heartbeat"),
        ("payments", "0016_learner_subscription"),
    ]

    operations = [
        migrations.AddField(
            model_name="courseenrollment",
            name="access_expires_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="courseenrollment",
            name="source_subscription",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="course_entitlements", to="payments.learnersubscription"),
        ),
        migrations.AddField(
            model_name="pdfpurchase",
            name="access_expires_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="pdfpurchase",
            name="source_subscription",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="pdf_entitlements", to="payments.learnersubscription"),
        ),
    ]
