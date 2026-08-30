import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0003_instructor_finance"),
        ("formations", "0003_formation_certificates"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddIndex(
            model_name="order",
            index=models.Index(fields=["status", "created_at"], name="payments_or_status_6f471d_idx"),
        ),
        migrations.AddIndex(
            model_name="order",
            index=models.Index(fields=["user", "status"], name="payments_or_user_id_8d1a2e_idx"),
        ),
        migrations.CreateModel(
            name="FormationSeatReservation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("expires_at", models.DateTimeField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("formation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="seat_reservations", to="formations.interactiveformation")),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="seat_reservations", to="payments.order")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="formation_seat_reservations", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name="formationseatreservation",
            constraint=models.UniqueConstraint(fields=("order", "formation"), name="uniq_order_formation_reservation"),
        ),
        migrations.AddIndex(
            model_name="formationseatreservation",
            index=models.Index(fields=["formation", "expires_at"], name="payments_fo_formati_7a9c55_idx"),
        ),
        migrations.AddIndex(
            model_name="formationseatreservation",
            index=models.Index(fields=["user", "expires_at"], name="payments_fo_user_id_0cb3d6_idx"),
        ),
    ]
