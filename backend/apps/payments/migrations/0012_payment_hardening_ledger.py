from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_financial_history(apps, schema_editor):
    Order = apps.get_model("payments", "Order")
    OrderItem = apps.get_model("payments", "OrderItem")
    InstructorPayout = apps.get_model("payments", "InstructorPayout")
    Ledger = apps.get_model("payments", "InstructorLedgerEntry")

    # Les commandes déjà remboursées n'avaient pas de timestamp de remboursement.
    for order in Order.objects.filter(status="refunded", refunded_at__isnull=True).iterator():
        Order.objects.filter(pk=order.pk).update(refunded_at=order.paid_at or order.created_at)

    # Une vente est enregistrée pour toute commande qui a effectivement été payée,
    # y compris celles remboursées ensuite. Le remboursement est une contre-écriture.
    items = OrderItem.objects.filter(
        order__status__in=["paid", "refunded"],
        instructor_id__isnull=False,
    ).exclude(instructor_earning_amount=0)
    for item in items.iterator():
        Ledger.objects.get_or_create(
            instructor_id=item.instructor_id,
            order_item_id=item.pk,
            entry_type="sale",
            defaults={
                "amount": item.instructor_earning_amount,
                "reference": f"order:{item.order_id}",
                "note": "Reprise historique de vente",
            },
        )
        if item.order.status == "refunded":
            Ledger.objects.get_or_create(
                instructor_id=item.instructor_id,
                order_item_id=item.pk,
                entry_type="refund",
                defaults={
                    "amount": -item.instructor_earning_amount,
                    "reference": f"refund:{item.order_id}",
                    "note": "Reprise historique de remboursement",
                },
            )

    for payout in InstructorPayout.objects.filter(status="paid").exclude(amount=0).iterator():
        Ledger.objects.get_or_create(
            instructor_id=payout.instructor_id,
            payout_id=payout.pk,
            entry_type="payout",
            defaults={
                "amount": -payout.amount,
                "reference": payout.reference or f"payout:{payout.pk}",
                "note": "Reprise historique de versement",
            },
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("payments", "0011_mentorship_order_items"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="checkout_url",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="order",
            name="idempotency_key",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name="order",
            name="request_fingerprint",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="order",
            name="refunded_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="order",
            name="refund_reference",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="order",
            name="refund_reason",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddConstraint(
            model_name="order",
            constraint=models.UniqueConstraint(
                fields=("user", "idempotency_key"),
                condition=~models.Q(idempotency_key=""),
                name="uniq_order_user_idempotency",
            ),
        ),
        migrations.CreateModel(
            name="InstructorLedgerEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("entry_type", models.CharField(choices=[("sale", "Vente"), ("refund", "Remboursement"), ("payout", "Versement"), ("adjustment", "Ajustement")], db_index=True, max_length=20)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("reference", models.CharField(blank=True, max_length=160)),
                ("note", models.CharField(blank=True, max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("instructor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ledger_entries", to=settings.AUTH_USER_MODEL)),
                ("order_item", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ledger_entries", to="payments.orderitem")),
                ("payout", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ledger_entries", to="payments.instructorpayout")),
            ],
            options={
                "ordering": ["-created_at", "-id"],
                "indexes": [
                    models.Index(fields=["instructor", "created_at"], name="ledger_instr_created_idx"),
                    models.Index(fields=["entry_type", "created_at"], name="ledger_type_created_idx"),
                ],
                "constraints": [
                    models.CheckConstraint(condition=~models.Q(amount=0), name="ledger_amount_nonzero"),
                    models.UniqueConstraint(fields=("order_item", "entry_type"), condition=models.Q(order_item__isnull=False, entry_type__in=["sale", "refund"]), name="uniq_ledger_item_type"),
                    models.UniqueConstraint(fields=("payout", "entry_type"), condition=models.Q(payout__isnull=False, entry_type="payout"), name="uniq_ledger_payout"),
                ],
            },
        ),
        migrations.RunPython(backfill_financial_history, noop_reverse),
    ]
