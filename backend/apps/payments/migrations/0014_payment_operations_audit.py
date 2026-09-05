from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0013_employer_entitlement_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="order", name="provider_status",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="order", name="payment_method",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="order", name="last_provider_check_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="order", name="expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="PaymentAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("attempt_number", models.PositiveIntegerField(default=1)),
                ("provider", models.CharField(max_length=30)),
                ("provider_sandbox", models.BooleanField(default=False)),
                ("provider_reference", models.CharField(blank=True, max_length=255)),
                ("status", models.CharField(choices=[("created", "Créée"), ("redirected", "Redirection créée"), ("pending", "En attente"), ("checked", "Vérifiée"), ("paid", "Payée"), ("failed", "Échouée"), ("error", "Erreur prestataire")], db_index=True, default="created", max_length=20)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("currency", models.CharField(max_length=3)),
                ("provider_status", models.CharField(blank=True, max_length=80)),
                ("payment_method", models.CharField(blank=True, max_length=80)),
                ("check_count", models.PositiveIntegerField(default=0)),
                ("error_count", models.PositiveIntegerField(default=0)),
                ("last_error", models.CharField(blank=True, max_length=500)),
                ("last_checked_at", models.DateTimeField(blank=True, null=True)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="payment_attempts", to="payments.order")),
            ],
            options={"ordering": ["-started_at", "-id"]},
        ),
        migrations.CreateModel(
            name="PaymentEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(blank=True, max_length=30)),
                ("provider_sandbox", models.BooleanField(default=False)),
                ("source", models.CharField(choices=[("checkout", "Checkout"), ("webhook", "Webhook"), ("confirm", "Vérification utilisateur"), ("reconciliation", "Réconciliation"), ("admin", "Administration"), ("system", "Système")], max_length=20)),
                ("event_type", models.CharField(db_index=True, max_length=100)),
                ("external_id", models.CharField(blank=True, max_length=191)),
                ("outcome", models.CharField(choices=[("received", "Reçu"), ("accepted", "Accepté"), ("ignored", "Ignoré"), ("rejected", "Rejeté"), ("error", "Erreur")], db_index=True, default="received", max_length=20)),
                ("payload_hash", models.CharField(blank=True, db_index=True, max_length=64)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("request_id", models.CharField(blank=True, db_index=True, max_length=100)),
                ("message", models.CharField(blank=True, max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("order", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="payment_events", to="payments.order")),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.CreateModel(
            name="PaymentIssue",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("issue_type", models.CharField(choices=[("amount_mismatch", "Montant incohérent"), ("currency_mismatch", "Devise incohérente"), ("provider_error", "Erreur prestataire répétée"), ("reference_mismatch", "Référence incohérente"), ("stale_pending", "Paiement en attente trop longtemps"), ("webhook_rejected", "Webhook rejeté")], db_index=True, max_length=40)),
                ("severity", models.CharField(choices=[("warning", "Avertissement"), ("critical", "Critique")], default="warning", max_length=20)),
                ("status", models.CharField(choices=[("open", "Ouverte"), ("resolved", "Résolue")], db_index=True, default="open", max_length=20)),
                ("message", models.CharField(max_length=500)),
                ("expected", models.JSONField(blank=True, default=dict)),
                ("observed", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("resolution_note", models.CharField(blank=True, max_length=500)),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="payment_issues", to="payments.order")),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.AddConstraint(model_name="paymentattempt", constraint=models.UniqueConstraint(fields=("order", "attempt_number"), name="uniq_payment_attempt_no")),
        migrations.AddIndex(model_name="paymentattempt", index=models.Index(fields=["provider", "status", "started_at"], name="pay_attempt_provider_idx")),
        migrations.AddIndex(model_name="paymentattempt", index=models.Index(fields=["order", "status"], name="pay_attempt_order_idx")),
        migrations.AddConstraint(model_name="paymentevent", constraint=models.UniqueConstraint(condition=~models.Q(external_id=""), fields=("provider", "provider_sandbox", "external_id"), name="uniq_payment_external_event")),
        migrations.AddIndex(model_name="paymentevent", index=models.Index(fields=["order", "created_at"], name="pay_event_order_created_idx")),
        migrations.AddIndex(model_name="paymentevent", index=models.Index(fields=["provider", "source", "created_at"], name="pay_event_provider_src_idx")),
        migrations.AddConstraint(model_name="paymentissue", constraint=models.UniqueConstraint(condition=models.Q(status="open"), fields=("order", "issue_type"), name="uniq_open_payment_issue")),
        migrations.AddIndex(model_name="paymentissue", index=models.Index(fields=["status", "severity", "created_at"], name="pay_issue_status_idx")),
    ]
