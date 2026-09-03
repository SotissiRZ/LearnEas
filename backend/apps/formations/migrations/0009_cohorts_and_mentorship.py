import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("formations", "0008_whiteboard_signal"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="interactiveformation",
            name="kind",
            field=models.CharField(
                choices=[("cohort", "Cohorte"), ("mentorship", "Conteneur mentorat")],
                db_index=True,
                default="cohort",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="interactiveformation",
            name="cohort_name",
            field=models.CharField(blank=True, help_text="Ex : Cohorte Septembre 2026", max_length=120),
        ),
        migrations.AddField(
            model_name="interactiveformation",
            name="cohort_timezone",
            field=models.CharField(default="Africa/Abidjan", max_length=64),
        ),
        migrations.AddField(
            model_name="interactiveformation",
            name="enrollment_deadline",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="interactiveformation",
            name="min_students",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.CreateModel(
            name="MentorshipOffering",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=180)),
                ("slug", models.SlugField(blank=True, max_length=200, unique=True)),
                ("description", models.TextField()),
                ("duration_minutes", models.PositiveSmallIntegerField(default=30)),
                ("price", models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ("language", models.CharField(default="Français", max_length=50)),
                ("timezone", models.CharField(default="Africa/Abidjan", max_length=64)),
                ("booking_notice_hours", models.PositiveSmallIntegerField(default=2)),
                ("cancellation_notice_hours", models.PositiveSmallIntegerField(default=12)),
                ("published", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("instructor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="mentorship_offerings", to=settings.AUTH_USER_MODEL)),
                ("room_formation", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="mentorship_container_for", to="formations.interactiveformation")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="MentorshipSlot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("starts_at", models.DateTimeField()),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("offering", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="slots", to="formations.mentorshipoffering")),
                ("session", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="mentorship_slot", to="formations.formationsession")),
            ],
            options={"ordering": ["starts_at"]},
        ),
        migrations.CreateModel(
            name="MentorshipBooking",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("pending_payment", "Paiement en attente"), ("confirmed", "Confirmée"), ("completed", "Terminée"), ("cancelled", "Annulée"), ("expired", "Expirée")], default="pending_payment", max_length=20)),
                ("price_snapshot", models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("confirmed_at", models.DateTimeField(blank=True, null=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("learner_note", models.TextField(blank=True)),
                ("mentor_note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("offering", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="bookings", to="formations.mentorshipoffering")),
                ("slot", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="bookings", to="formations.mentorshipslot")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="mentorship_bookings", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="mentorshipoffering",
            index=models.Index(fields=["published", "instructor"], name="mentor_offer_pub_instr_idx"),
        ),
        migrations.AddConstraint(
            model_name="mentorshipslot",
            constraint=models.UniqueConstraint(fields=("offering", "starts_at"), name="uniq_mentor_offer_start"),
        ),
        migrations.AddIndex(
            model_name="mentorshipslot",
            index=models.Index(fields=["offering", "starts_at", "is_active"], name="mentor_slot_offer_time_idx"),
        ),
        migrations.AddConstraint(
            model_name="mentorshipbooking",
            constraint=models.UniqueConstraint(condition=models.Q(status__in=["pending_payment", "confirmed"]), fields=("slot",), name="uniq_active_mentor_slot_booking"),
        ),
        migrations.AddIndex(
            model_name="mentorshipbooking",
            index=models.Index(fields=["user", "status"], name="mentor_book_user_status_idx"),
        ),
        migrations.AddIndex(
            model_name="mentorshipbooking",
            index=models.Index(fields=["offering", "status"], name="mentor_book_offer_status_idx"),
        ),
    ]
