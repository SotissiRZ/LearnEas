from django.db import migrations, models
import django.db.models.deletion


def backfill_source_orders(apps, schema_editor):
    CourseEnrollment = apps.get_model("enrollments", "CourseEnrollment")
    PDFPurchase = apps.get_model("enrollments", "PDFPurchase")
    OrderItem = apps.get_model("payments", "OrderItem")

    for enrollment in CourseEnrollment.objects.filter(source_order__isnull=True).iterator():
        item = (
            OrderItem.objects.filter(
                course_id=enrollment.course_id,
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
        CourseEnrollment.objects.filter(pk=enrollment.pk).update(**updates)

    for purchase in PDFPurchase.objects.filter(source_order__isnull=True).iterator():
        item = (
            OrderItem.objects.filter(
                pdf_product_id=purchase.pdf_product_id,
                order__user_id=purchase.user_id,
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
        PDFPurchase.objects.filter(pk=purchase.pk).update(**updates)


def revoke_historical_certificates(apps, schema_editor):
    Certificate = apps.get_model("enrollments", "Certificate")
    Event = apps.get_model("enrollments", "CertificateEvent")

    certs = Certificate.objects.filter(status="active").filter(
        models.Q(course_enrollment__revoked_at__isnull=False) |
        models.Q(formation_enrollment__revoked_at__isnull=False)
    )
    for cert in certs.iterator():
        when = None
        if cert.course_enrollment_id:
            when = cert.course_enrollment.revoked_at
        elif cert.formation_enrollment_id:
            when = cert.formation_enrollment.revoked_at
        Certificate.objects.filter(pk=cert.pk).update(
            status="revoked",
            revoked_at=when,
            revocation_reason="Remboursement historique",
        )
        Event.objects.create(
            certificate_id=cert.pk,
            event_type="revoked",
            details={"reason": "Remboursement historique", "backfilled": True},
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("enrollments", "0005_verifiable_credentials"),
        ("formations", "0010_revocable_entitlements"),
        ("payments", "0012_payment_hardening_ledger"),
    ]

    operations = [
        migrations.AddField(
            model_name="courseenrollment",
            name="source_order",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="course_entitlements", to="payments.order"),
        ),
        migrations.AddField(
            model_name="courseenrollment",
            name="revoked_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="courseenrollment",
            name="revocation_reason",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="pdfpurchase",
            name="source_order",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="pdf_entitlements", to="payments.order"),
        ),
        migrations.AddField(
            model_name="pdfpurchase",
            name="revoked_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="pdfpurchase",
            name="revocation_reason",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.RunPython(backfill_source_orders, noop_reverse),
        migrations.RunPython(revoke_historical_certificates, noop_reverse),
        migrations.AlterField(
            model_name="certificate",
            name="course_enrollment",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="certificate_records", to="enrollments.courseenrollment"),
        ),
        migrations.AlterField(
            model_name="certificate",
            name="formation_enrollment",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="certificate_records", to="formations.formationenrollment"),
        ),
        migrations.RemoveConstraint(
            model_name="certificate",
            name="certificate_exactly_one_enrollment",
        ),
        migrations.AddConstraint(
            model_name="certificate",
            constraint=models.CheckConstraint(
                condition=~models.Q(course_enrollment__isnull=False, formation_enrollment__isnull=False),
                name="certificate_not_two_enrollments",
            ),
        ),
    ]
