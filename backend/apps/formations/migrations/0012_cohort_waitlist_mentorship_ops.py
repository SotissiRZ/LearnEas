from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("formations", "0011_rename_formations__session_727f67_idx_formations__session_c9693c_idx_and_more"),
        ("payments", "0014_payment_operations_audit"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="FormationWaitlistEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("waiting", "En attente"), ("offered", "Place proposée"), ("joined", "Inscrit"), ("cancelled", "Annulé"), ("expired", "Offre expirée")], db_index=True, default="waiting", max_length=16)),
                ("offered_at", models.DateTimeField(blank=True, null=True)),
                ("offer_expires_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("joined_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("formation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="waitlist_entries", to="formations.interactiveformation")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="formation_waitlist_entries", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["created_at", "id"]},
        ),
        migrations.AddConstraint(
            model_name="formationwaitlistentry",
            constraint=models.UniqueConstraint(fields=("formation", "user"), name="uniq_formation_waitlist_user"),
        ),
        migrations.AddIndex(
            model_name="formationwaitlistentry",
            index=models.Index(fields=["formation", "status", "created_at"], name="form_wait_status_created_idx"),
        ),
        migrations.CreateModel(
            name="MentorshipPack",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sessions_count", models.PositiveSmallIntegerField(default=3)),
                ("price", models.DecimalField(decimal_places=2, max_digits=8)),
                ("validity_days", models.PositiveIntegerField(default=180)),
                ("published", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("offering", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="packs", to="formations.mentorshipoffering")),
            ],
            options={"ordering": ["sessions_count", "price"]},
        ),
        migrations.AddConstraint(
            model_name="mentorshippack",
            constraint=models.UniqueConstraint(fields=("offering", "sessions_count"), name="uniq_mentor_pack_sessions"),
        ),
        migrations.AddConstraint(
            model_name="mentorshippack",
            constraint=models.CheckConstraint(condition=models.Q(("sessions_count__gte", 2)), name="mentor_pack_sessions_gte2"),
        ),
        migrations.AddConstraint(
            model_name="mentorshippack",
            constraint=models.CheckConstraint(condition=models.Q(("price__gte", 0)), name="mentor_pack_price_gte0"),
        ),
        migrations.CreateModel(
            name="MentorshipAvailabilityRule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("weekday", models.PositiveSmallIntegerField(help_text="0=lundi … 6=dimanche")),
                ("start_time", models.TimeField()),
                ("end_time", models.TimeField()),
                ("interval_minutes", models.PositiveSmallIntegerField(default=60)),
                ("valid_from", models.DateField(default=django.utils.timezone.localdate)),
                ("valid_until", models.DateField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("offering", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="availability_rules", to="formations.mentorshipoffering")),
            ],
            options={"ordering": ["weekday", "start_time"]},
        ),
        migrations.AddConstraint(
            model_name="mentorshipavailabilityrule",
            constraint=models.CheckConstraint(condition=models.Q(("weekday__gte", 0), ("weekday__lte", 6)), name="mentor_rule_weekday_range"),
        ),
        migrations.AddConstraint(
            model_name="mentorshipavailabilityrule",
            constraint=models.CheckConstraint(condition=models.Q(("interval_minutes__gte", 15)), name="mentor_rule_interval_gte15"),
        ),
        migrations.CreateModel(
            name="MentorshipPass",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("total_sessions", models.PositiveSmallIntegerField()),
                ("remaining_sessions", models.PositiveSmallIntegerField()),
                ("expires_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("pack", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="passes", to="formations.mentorshippack")),
                ("source_order", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="mentorship_passes", to="payments.order")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="mentorship_passes", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="mentorshippass",
            constraint=models.CheckConstraint(condition=models.Q(("remaining_sessions__lte", models.F("total_sessions"))), name="mentor_pass_remaining_lte_total"),
        ),
        migrations.AddConstraint(
            model_name="mentorshippass",
            constraint=models.UniqueConstraint(condition=models.Q(("source_order__isnull", False)), fields=("user", "pack", "source_order"), name="uniq_mentor_pass_paid_source"),
        ),
        migrations.AddIndex(
            model_name="mentorshippass",
            index=models.Index(fields=["user", "revoked_at", "expires_at"], name="mentor_pass_user_active_idx"),
        ),
        migrations.AddField(
            model_name="mentorshipslot",
            name="availability_rule",
            field=models.ForeignKey(blank=True, help_text="Règle récurrente ayant généré ce créneau ; vide pour un créneau manuel.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="generated_slots", to="formations.mentorshipavailabilityrule"),
        ),
        migrations.AddField(
            model_name="mentorshipbooking",
            name="mentorship_pass",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="bookings", to="formations.mentorshippass"),
        ),
        migrations.AddField(
            model_name="mentorshipbooking",
            name="reschedule_count",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="mentorshipbooking",
            name="rescheduled_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
