from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="ProductEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_name", models.CharField(choices=[("page_view", "Page vue"), ("search_submitted", "Recherche lancée"), ("discovery_result_clicked", "Résultat de recherche ouvert"), ("recommendation_clicked", "Recommandation ouverte"), ("course_viewed", "Cours consulté"), ("formation_viewed", "Formation consultée"), ("pdf_viewed", "PDF consulté"), ("opportunity_viewed", "Opportunité consultée"), ("video_started", "Vidéo démarrée"), ("video_completed", "Vidéo terminée")], db_index=True, max_length=64)),
                ("session_key", models.CharField(blank=True, db_index=True, max_length=64)),
                ("path", models.CharField(blank=True, db_index=True, max_length=240)),
                ("properties", models.JSONField(blank=True, default=dict)),
                ("occurred_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="product_events", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-occurred_at", "-id"]},
        ),
        migrations.AddIndex(model_name="productevent", index=models.Index(fields=["event_name", "-occurred_at"], name="analytics_event_time_idx")),
        migrations.AddIndex(model_name="productevent", index=models.Index(fields=["user", "-occurred_at"], name="analytics_user_time_idx")),
        migrations.AddIndex(model_name="productevent", index=models.Index(fields=["session_key", "-occurred_at"], name="analytics_session_time_idx")),
    ]
