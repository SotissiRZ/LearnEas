from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0004_catalog_query_indexes"),
        ("enrollments", "0003_wishlist_constraints"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="lessonprogress",
            name="last_position_seconds",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.CreateModel(
            name="LessonNote",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("timestamp_seconds", models.PositiveIntegerField(default=0)),
                ("content", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("lesson", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="learner_notes", to="catalog.lesson")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lesson_notes", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["lesson__section__order", "lesson__order", "timestamp_seconds", "created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="lessonnote",
            index=models.Index(fields=["user", "lesson", "timestamp_seconds"], name="enr_note_user_lesson_ts"),
        ),
    ]
