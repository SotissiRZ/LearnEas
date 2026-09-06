from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0015_mentorship_packs"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="orderitem",
            name="item_type",
            field=models.CharField(
                choices=[
                    ("course", "Cours"),
                    ("pdf", "PDF"),
                    ("formation", "Formation interactive"),
                    ("mentoring", "Mentorat"),
                    ("mentor_pack", "Pack mentorat"),
                    ("employer", "Droit recruteur"),
                    ("learner_subscription", "Abonnement apprenant"),
                ],
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="LearnerSubscription",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("starts_at", models.DateTimeField(db_index=True)),
                ("ends_at", models.DateTimeField(db_index=True)),
                ("revoked_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("revocation_reason", models.CharField(blank=True, max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("source_order", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="learner_subscription", to="payments.order")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="learner_subscriptions", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-starts_at", "-id"]},
        ),
        migrations.AddIndex(
            model_name="learnersubscription",
            index=models.Index(fields=["user", "ends_at"], name="pay_learnsub_user_end_idx"),
        ),
    ]
