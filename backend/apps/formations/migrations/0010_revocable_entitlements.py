from django.db import migrations, models
import django.db.models.deletion


def backfill_source_orders(apps, schema_editor):
    Enrollment = apps.get_model("formations", "FormationEnrollment")
    OrderItem = apps.get_model("payments", "OrderItem")

    for enrollment in Enrollment.objects.filter(source_order__isnull=True).iterator():
        item = (
            OrderItem.objects.filter(
                formation_id=enrollment.formation_id,
                order__user_id=enrollment.user_id,
                order__status__in=["paid", "refunded"],
            )
            .select_related("order")
            .order_by("-order__paid_at", "-order__created_at", "-id")
            .first()
        )
        if not item:
            continue
        updates = {"source_order_id": item.order_id}
        if item.order.status == "refunded":
            updates.update({
                "revoked_at": item.order.refunded_at or item.order.paid_at or item.order.created_at,
                "revocation_reason": "Remboursement historique",
            })
        Enrollment.objects.filter(pk=enrollment.pk).update(**updates)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("formations", "0009_cohorts_and_mentorship"),
        ("payments", "0012_payment_hardening_ledger"),
    ]

    operations = [
        migrations.AddField(
            model_name="formationenrollment",
            name="source_order",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="formation_entitlements", to="payments.order"),
        ),
        migrations.AddField(
            model_name="formationenrollment",
            name="revoked_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="formationenrollment",
            name="revocation_reason",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.RunPython(backfill_source_orders, noop_reverse),
    ]
