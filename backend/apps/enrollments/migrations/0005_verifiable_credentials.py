import hashlib
import json

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_certificate_proofs(apps, schema_editor):
    Certificate = apps.get_model("enrollments", "Certificate")
    CertificateEvent = apps.get_model("enrollments", "CertificateEvent")
    PlatformSettings = apps.get_model("accounts", "PlatformSettings")
    config = PlatformSettings.objects.filter(pk=1).first()
    issuer_name = "LearnEas"
    issuer_country = ""
    if config:
        issuer_name = (getattr(config, "legal_company_name", "") or getattr(config, "site_name", "") or "LearnEas").strip()
        issuer_country = (getattr(config, "legal_country", "") or "").strip()

    for cert in Certificate.objects.all().iterator():
        payload = {
            "schema_version": 1,
            "certificate_number": cert.certificate_number,
            "verification_code": str(cert.verification_code),
            "student_name": cert.student_name,
            "content_type": cert.content_type,
            "content_title": cert.content_title,
            "instructor_name": cert.instructor_name,
            "issuer_name": issuer_name,
            "issuer_country": issuer_country,
            "achievement_percent": str(cert.achievement_percent),
            "completed_at": cert.completed_at.isoformat() if cert.completed_at else None,
            "expires_at": cert.expires_at.isoformat() if cert.expires_at else None,
            "skills": [],
            "projects": [],
        }
        digest = hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        Certificate.objects.filter(pk=cert.pk).update(
            issuer_name=issuer_name,
            issuer_country=issuer_country,
            skills_snapshot=[],
            projects_snapshot=[],
            credential_digest=digest,
            schema_version=1,
        )
        CertificateEvent.objects.get_or_create(
            certificate_id=cert.pk,
            event_type="issued",
            defaults={"actor_id": cert.issued_by_id, "details": {"backfilled": True}},
        )
        if cert.status == "revoked":
            CertificateEvent.objects.get_or_create(
                certificate_id=cert.pk,
                event_type="revoked",
                defaults={
                    "actor_id": cert.issued_by_id,
                    "details": {"reason": cert.revocation_reason or "", "backfilled": True},
                },
            )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("enrollments", "0004_lessonnote"),
        ("accounts", "0006_whatsapp_platform_settings"),
    ]

    operations = [
        migrations.AlterField(
            model_name="certificate",
            name="course_enrollment",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="certificate_records",
                to="enrollments.courseenrollment",
            ),
        ),
        migrations.AlterField(
            model_name="certificate",
            name="formation_enrollment",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="certificate_records",
                to="formations.formationenrollment",
            ),
        ),
        migrations.AddField(
            model_name="certificate",
            name="supersedes",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="replacement_certificates",
                to="enrollments.certificate",
            ),
        ),
        migrations.AddField(
            model_name="certificate",
            name="issuer_name",
            field=models.CharField(blank=True, max_length=180),
        ),
        migrations.AddField(
            model_name="certificate",
            name="issuer_country",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="certificate",
            name="skills_snapshot",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="certificate",
            name="projects_snapshot",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="certificate",
            name="credential_digest",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AddField(
            model_name="certificate",
            name="schema_version",
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.CreateModel(
            name="CertificateEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(choices=[("issued", "Émis"), ("revoked", "Révoqué"), ("reissued", "Réémis"), ("expired", "Expiré")], db_index=True, max_length=20)),
                ("details", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="certificate_events", to=settings.AUTH_USER_MODEL)),
                ("certificate", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="events", to="enrollments.certificate")),
            ],
            options={
                "ordering": ["-created_at", "-id"],
                "indexes": [models.Index(fields=["certificate", "-created_at"], name="cert_event_cert_created_idx")],
            },
        ),
        migrations.RunPython(backfill_certificate_proofs, noop_reverse),
        migrations.AlterField(
            model_name="certificate",
            name="schema_version",
            field=models.PositiveSmallIntegerField(default=2),
        ),
        migrations.AddConstraint(
            model_name="certificate",
            constraint=models.UniqueConstraint(
                fields=("course_enrollment",),
                condition=models.Q(course_enrollment__isnull=False, status="active"),
                name="uniq_active_course_certificate",
            ),
        ),
        migrations.AddConstraint(
            model_name="certificate",
            constraint=models.UniqueConstraint(
                fields=("formation_enrollment",),
                condition=models.Q(formation_enrollment__isnull=False, status="active"),
                name="uniq_active_formation_certificate",
            ),
        ),
    ]
