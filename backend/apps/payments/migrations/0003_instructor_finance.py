import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from decimal import Decimal, ROUND_HALF_UP


def backfill_orderitem_finance(apps, schema_editor):
    """Backfill historique : rattache le vendeur et calcule le split 15/85 existant par défaut."""
    OrderItem = apps.get_model("payments", "OrderItem")
    Course = apps.get_model("catalog", "Course")
    PDFProduct = apps.get_model("catalog", "PDFProduct")
    Formation = apps.get_model("formations", "InteractiveFormation")

    course_owners = dict(Course.objects.values_list("id", "instructor_id"))
    pdf_owners = dict(PDFProduct.objects.values_list("id", "instructor_id"))
    formation_owners = dict(Formation.objects.values_list("id", "instructor_id"))
    pct = Decimal("15") / Decimal("100")
    cent = Decimal("0.01")

    for item in OrderItem.objects.all().iterator():
        instructor_id = None
        if item.course_id:
            instructor_id = course_owners.get(item.course_id)
        elif item.pdf_product_id:
            instructor_id = pdf_owners.get(item.pdf_product_id)
        elif item.formation_id:
            instructor_id = formation_owners.get(item.formation_id)

        gross = Decimal(item.unit_price or 0)
        fee = (gross * pct).quantize(cent, rounding=ROUND_HALF_UP)
        earning = (gross - fee).quantize(cent, rounding=ROUND_HALF_UP)
        OrderItem.objects.filter(pk=item.pk).update(
            instructor_id=instructor_id,
            platform_fee_amount=fee,
            instructor_earning_amount=earning,
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("formations", "0002_internal_live_sessions"),
        ("payments", "0002_orderitem_formation_alter_order_provider_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(model_name="orderitem", name="instructor", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sold_order_items", to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name="orderitem", name="platform_fee_amount", field=models.DecimalField(decimal_places=2, default=0, max_digits=8)),
        migrations.AddField(model_name="orderitem", name="instructor_earning_amount", field=models.DecimalField(decimal_places=2, default=0, max_digits=8)),
        migrations.RunPython(backfill_orderitem_finance, noop_reverse),
        migrations.CreateModel(
            name="PayoutProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("method", models.CharField(choices=[("bank", "Virement bancaire"), ("mobile_money", "Mobile Money"), ("paypal", "PayPal")], default="bank", max_length=20)),
                ("account_name", models.CharField(blank=True, max_length=150)),
                ("account_reference", models.CharField(blank=True, help_text="IBAN/RIB, numéro Mobile Money ou email PayPal selon la méthode.", max_length=255)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("instructor", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="payout_profile", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="InstructorPayout",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("status", models.CharField(choices=[("pending", "Demandé"), ("processing", "En traitement"), ("paid", "Payé"), ("failed", "Échoué"), ("cancelled", "Annulé")], default="pending", max_length=20)),
                ("method", models.CharField(choices=[("bank", "Virement bancaire"), ("mobile_money", "Mobile Money"), ("paypal", "PayPal")], max_length=20)),
                ("account_reference_snapshot", models.CharField(blank=True, max_length=255)),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
                ("reference", models.CharField(blank=True, max_length=120)),
                ("note", models.TextField(blank=True)),
                ("instructor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="payouts", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-requested_at"]},
        ),
    ]
