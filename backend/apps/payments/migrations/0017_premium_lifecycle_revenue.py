from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0016_learner_subscription"),
        ("accounts", "0013_premium_creator_pool"),
        ("catalog", "0008_premium_catalog"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="learnersubscription",
            name="creator_pool_amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="learnersubscription",
            name="platform_revenue_amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="learnersubscription",
            name="revenue_settled_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.CreateModel(
            name="PremiumRenewalProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("enabled", models.BooleanField(default=False)),
                ("status", models.CharField(choices=[("scheduled", "Planifié"), ("action_required", "Action requise"), ("past_due", "Échu"), ("paused", "En pause"), ("cancelled", "Annulé")], db_index=True, default="paused", max_length=24)),
                ("provider", models.CharField(choices=[("stripe", "Stripe"), ("youcanpay", "YouCan Pay"), ("geniuspay", "GeniusPay"), ("cinetpay", "CinetPay Mobile Money"), ("manual", "Paiement manuel")], default="stripe", max_length=30)),
                ("currency", models.CharField(default="EUR", max_length=3)),
                ("next_renewal_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("grace_ends_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("last_attempt_at", models.DateTimeField(blank=True, null=True)),
                ("failure_count", models.PositiveSmallIntegerField(default=0)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("last_order", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="premium_renewal_profiles", to="payments.order")),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="premium_renewal_profile", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="PremiumContentUsage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("interaction_count", models.PositiveIntegerField(default=0)),
                ("watched_seconds", models.PositiveIntegerField(default=0)),
                ("first_used_at", models.DateTimeField(auto_now_add=True)),
                ("last_used_at", models.DateTimeField(auto_now=True, db_index=True)),
                ("course", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="premium_usage", to="catalog.course")),
                ("instructor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="premium_content_usage", to=settings.AUTH_USER_MODEL)),
                ("pdf_product", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="premium_usage", to="catalog.pdfproduct")),
                ("subscription", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="content_usage", to="payments.learnersubscription")),
            ],
        ),
        migrations.CreateModel(
            name="PremiumRevenueAllocation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("usage_weight", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("creator_pool_amount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("reversed_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("instructor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="premium_revenue_allocations", to=settings.AUTH_USER_MODEL)),
                ("subscription", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="revenue_allocations", to="payments.learnersubscription")),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.AddField(
            model_name="instructorledgerentry",
            name="premium_allocation",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ledger_entries", to="payments.premiumrevenueallocation"),
        ),
        migrations.AlterField(
            model_name="instructorledgerentry",
            name="entry_type",
            field=models.CharField(choices=[("sale", "Vente"), ("refund", "Remboursement"), ("payout", "Versement"), ("adjustment", "Ajustement"), ("premium", "Part Premium"), ("premium_refund", "Reprise Premium")], db_index=True, max_length=20),
        ),
        migrations.AddIndex(
            model_name="premiumrenewalprofile",
            index=models.Index(fields=["enabled", "next_renewal_at"], name="pay_premrenew_due_idx"),
        ),
        migrations.AddConstraint(
            model_name="premiumcontentusage",
            constraint=models.CheckConstraint(condition=(models.Q(course__isnull=False, pdf_product__isnull=True) | models.Q(course__isnull=True, pdf_product__isnull=False)), name="prem_usage_one_content"),
        ),
        migrations.AddConstraint(
            model_name="premiumcontentusage",
            constraint=models.UniqueConstraint(condition=models.Q(course__isnull=False), fields=("subscription", "course"), name="uniq_prem_usage_course"),
        ),
        migrations.AddConstraint(
            model_name="premiumcontentusage",
            constraint=models.UniqueConstraint(condition=models.Q(pdf_product__isnull=False), fields=("subscription", "pdf_product"), name="uniq_prem_usage_pdf"),
        ),
        migrations.AddIndex(
            model_name="premiumcontentusage",
            index=models.Index(fields=["subscription", "instructor"], name="pay_premusage_instr_idx"),
        ),
        migrations.AddConstraint(
            model_name="premiumrevenueallocation",
            constraint=models.UniqueConstraint(fields=("subscription", "instructor"), name="uniq_prem_alloc_instr"),
        ),
        migrations.AddConstraint(
            model_name="premiumrevenueallocation",
            constraint=models.CheckConstraint(condition=models.Q(amount__gt=0), name="prem_alloc_amount_gt_zero"),
        ),
        migrations.AddIndex(
            model_name="premiumrevenueallocation",
            index=models.Index(fields=["instructor", "created_at"], name="pay_premalloc_instr_idx"),
        ),
        migrations.AddConstraint(
            model_name="instructorledgerentry",
            constraint=models.UniqueConstraint(
                condition=models.Q(premium_allocation__isnull=False, entry_type__in=["premium", "premium_refund"]),
                fields=("premium_allocation", "entry_type"),
                name="uniq_ledger_premium_alloc_type",
            ),
        ),
    ]
