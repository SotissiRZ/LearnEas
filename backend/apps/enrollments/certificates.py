import uuid
from datetime import timedelta
from decimal import Decimal
from django.db.models import Sum
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import PlatformSettings
from apps.formations.models import FormationAttendance
from .models import Certificate


def _name(user):
    return user.get_full_name() or user.username


def _expires(months):
    return timezone.now() + timedelta(days=int(months) * 30) if months else None


def course_eligibility(enrollment):
    course = enrollment.course
    threshold = max(0, min(int(course.certificate_threshold_percent or 100), 100))
    percent = int(enrollment.progress_percent or 0)
    return {
        "eligible": bool(course.certificate_enabled and percent >= threshold),
        "percent": percent,
        "threshold": threshold,
        "reason": "" if percent >= threshold else f"Progression requise : {threshold} %.",
    }


def formation_attendance_percent(enrollment):
    sessions = list(enrollment.formation.sessions.all())
    if not sessions:
        return 0
    expected_total = 0
    attended_total = 0
    for session in sessions:
        expected = int(session.actual_duration_seconds or (session.duration_minutes or 0) * 60)
        if expected <= 0:
            continue
        expected_total += expected
        seconds = (
            FormationAttendance.objects.filter(session=session, user=enrollment.user)
            .aggregate(total=Sum("duration_seconds"))["total"]
            or 0
        )
        attended_total += min(int(seconds), expected)
    if expected_total <= 0:
        return 0
    return min(round(attended_total * 100 / expected_total, 2), 100)


def formation_eligibility(enrollment):
    formation = enrollment.formation
    threshold = max(0, min(int(formation.certificate_attendance_percent or 80), 100))
    percent = formation_attendance_percent(enrollment)
    return {
        "eligible": bool(formation.certificate_enabled and percent >= threshold),
        "percent": percent,
        "threshold": threshold,
        "reason": "" if percent >= threshold else f"Présence requise : {threshold} %.",
    }


def _certificate_number(prefix):
    clean = (prefix or "LE-CERT").strip().upper().replace(" ", "-")[:30]
    return f"{clean}-{timezone.now():%Y}-{uuid.uuid4().hex[:10].upper()}"


def issue_course_certificate(enrollment, issued_by=None, force=False):
    course = enrollment.course
    eligibility = course_eligibility(enrollment)
    if not force and not eligibility["eligible"]:
        raise ValueError(eligibility["reason"] or "L'apprenant n'est pas encore éligible.")
    existing = Certificate.objects.filter(course_enrollment=enrollment).first()
    if existing and existing.effective_status == Certificate.Status.ACTIVE:
        return existing, False
    cert = existing or Certificate(course_enrollment=enrollment, user=enrollment.user)
    cert.user = enrollment.user
    cert.issued_by = issued_by
    cert.certificate_number = _certificate_number(course.certificate_number_prefix)
    cert.verification_code = uuid.uuid4()
    cert.status = Certificate.Status.ACTIVE
    cert.expires_at = _expires(course.certificate_validity_months)
    cert.revoked_at = None
    cert.revocation_reason = ""
    cert.achievement_percent = Decimal(str(eligibility["percent"]))
    cert.student_name = _name(enrollment.user)
    cert.content_type = "course"
    cert.content_title = course.title
    cert.instructor_name = _name(course.instructor)
    cert.title = course.certificate_title
    cert.subtitle = course.certificate_subtitle
    cert.description = course.certificate_description
    cert.signatory_name = course.certificate_signatory_name or _name(course.instructor)
    cert.signatory_title = course.certificate_signatory_title or "Instructeur"
    cert.accent_color = course.certificate_accent_color
    cert.duration_minutes = course.total_duration_minutes
    cert.completed_at = enrollment.completed_at or timezone.now()
    cert.display_options = {
        "show_duration": course.certificate_show_duration,
        "show_instructor": course.certificate_show_instructor,
        "show_completion_date": course.certificate_show_completion_date,
    }
    cert.metadata = {"course_id": course.id, "enrollment_id": enrollment.id, "threshold": eligibility["threshold"]}
    cert.save()
    if not enrollment.certificate_issued:
        enrollment.certificate_issued = True
        enrollment.save(update_fields=["certificate_issued"])
    try:
        from apps.notifications.services import queue_certificate_ready
        transaction.on_commit(lambda certificate_id=cert.id: queue_certificate_ready(certificate_id))
    except Exception:
        pass
    return cert, existing is None


def issue_formation_certificate(enrollment, issued_by=None, force=False):
    formation = enrollment.formation
    eligibility = formation_eligibility(enrollment)
    if not force and not eligibility["eligible"]:
        raise ValueError(eligibility["reason"] or "L'apprenant n'est pas encore éligible.")
    existing = Certificate.objects.filter(formation_enrollment=enrollment).first()
    if existing and existing.effective_status == Certificate.Status.ACTIVE:
        return existing, False
    cert = existing or Certificate(formation_enrollment=enrollment, user=enrollment.user)
    cert.user = enrollment.user
    cert.issued_by = issued_by
    cert.certificate_number = _certificate_number(formation.certificate_number_prefix)
    cert.verification_code = uuid.uuid4()
    cert.status = Certificate.Status.ACTIVE
    cert.expires_at = _expires(formation.certificate_validity_months)
    cert.revoked_at = None
    cert.revocation_reason = ""
    cert.achievement_percent = Decimal(str(eligibility["percent"]))
    cert.student_name = _name(enrollment.user)
    cert.content_type = "formation"
    cert.content_title = formation.title
    cert.instructor_name = _name(formation.instructor)
    cert.title = formation.certificate_title
    cert.subtitle = formation.certificate_subtitle
    cert.description = formation.certificate_description
    cert.signatory_name = formation.certificate_signatory_name or _name(formation.instructor)
    cert.signatory_title = formation.certificate_signatory_title or "Organisateur"
    cert.accent_color = formation.certificate_accent_color
    cert.duration_minutes = sum(s.duration_minutes for s in formation.sessions.all())
    cert.completed_at = timezone.now()
    cert.display_options = {
        "show_duration": formation.certificate_show_duration,
        "show_instructor": formation.certificate_show_instructor,
        "show_completion_date": formation.certificate_show_completion_date,
    }
    cert.metadata = {"formation_id": formation.id, "enrollment_id": enrollment.id, "threshold": eligibility["threshold"]}
    cert.save()
    if not enrollment.certificate_issued:
        enrollment.certificate_issued = True
        enrollment.save(update_fields=["certificate_issued"])
    try:
        from apps.notifications.services import queue_certificate_ready
        transaction.on_commit(lambda certificate_id=cert.id: queue_certificate_ready(certificate_id))
    except Exception:
        pass
    return cert, existing is None


def apply_platform_certificate_defaults(instance, kind="course"):
    config = PlatformSettings.load()
    instance.certificate_enabled = config.certificate_default_enabled
    instance.certificate_auto_issue = config.certificate_default_auto_issue
    if kind == "course":
        instance.certificate_threshold_percent = config.certificate_default_threshold_percent
    else:
        instance.certificate_attendance_percent = config.certificate_default_attendance_percent
    instance.certificate_validity_months = config.certificate_default_validity_months
    instance.certificate_title = config.certificate_default_title
    instance.certificate_subtitle = config.certificate_default_subtitle
    instance.certificate_signatory_name = config.certificate_default_signatory_name
    instance.certificate_signatory_title = config.certificate_default_signatory_title
    instance.certificate_accent_color = config.certificate_default_accent_color
    instance.certificate_number_prefix = config.certificate_default_number_prefix if kind == "course" else "LE-LIVE"
    return instance
