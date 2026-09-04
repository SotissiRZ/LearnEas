import hashlib
import json
import uuid
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.accounts.models import PlatformSettings
from apps.formations.models import FormationAttendance
from .models import Certificate, CertificateEvent


def _name(user):
    return user.get_full_name() or user.username


def _expires(months):
    return timezone.now() + timedelta(days=int(months) * 30) if months else None


def _clean_strings(values, limit=40):
    result = []
    seen = set()
    for raw in values or []:
        value = str(raw or "").strip()
        if not value:
            continue
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(value[:160])
        if len(result) >= limit:
            break
    return result


def course_eligibility(enrollment):
    course = enrollment.course
    threshold = max(0, min(int(course.certificate_threshold_percent or 100), 100))
    percent = int(enrollment.progress_percent or 0)
    progress_ok = percent >= threshold
    from apps.projects.services import required_projects_status

    project_status = required_projects_status(enrollment)
    project_ok = project_status["complete"]
    project_reason = ""
    if not project_ok:
        missing_titles = [p.title for p in project_status["missing"][:3]]
        suffix = "…" if len(project_status["missing"]) > 3 else ""
        project_reason = "Projet(s) pratique(s) requis : " + ", ".join(missing_titles) + suffix + "."
    reason = ""
    if not progress_ok:
        reason = f"Progression requise : {threshold} %."
    elif not project_ok:
        reason = project_reason
    return {
        "eligible": bool(course.certificate_enabled and progress_ok and project_ok),
        "percent": percent,
        "threshold": threshold,
        "projects_complete": project_ok,
        "reason": reason,
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


def _course_evidence(enrollment):
    """Fige les compétences et projets réellement validés au moment de la certification."""
    from apps.projects.models import ProjectSubmission

    course = enrollment.course
    submissions = (
        ProjectSubmission.objects.filter(
            enrollment=enrollment,
            student=enrollment.user,
            assignment__course=course,
            status=ProjectSubmission.Status.APPROVED,
        )
        .select_related("assignment", "reviewed_by")
        .order_by("assignment__order", "assignment_id")
    )

    skills = list(course.what_you_will_learn or [])
    projects = []
    for submission in submissions:
        assignment = submission.assignment
        skills.extend(assignment.skills or [])
        skills.extend(submission.skills or [])
        projects.append(
            {
                "title": assignment.title,
                "required_for_certificate": bool(assignment.required_for_certificate),
                "score": float(submission.score) if submission.score is not None else None,
                "max_score": int(assignment.max_score or 100),
                "validated_at": submission.reviewed_at.isoformat() if submission.reviewed_at else None,
                "validated_by": _name(submission.reviewed_by) if submission.reviewed_by else _name(course.instructor),
                "skills": _clean_strings(list(assignment.skills or []) + list(submission.skills or []), limit=20),
            }
        )
    return _clean_strings(skills), projects


def _issuer_snapshot():
    config = PlatformSettings.load()
    return {
        "name": (config.legal_company_name or config.site_name or "KalanPro").strip(),
        "country": (config.legal_country or "").strip(),
    }


def _credential_digest(certificate):
    """Empreinte SHA-256 du snapshot public. Ce n'est pas une signature numérique qualifiée."""
    payload = {
        "schema_version": int(certificate.schema_version or 2),
        "certificate_number": certificate.certificate_number,
        "verification_code": str(certificate.verification_code),
        "student_name": certificate.student_name,
        "content_type": certificate.content_type,
        "content_title": certificate.content_title,
        "instructor_name": certificate.instructor_name,
        "issuer_name": certificate.issuer_name,
        "issuer_country": certificate.issuer_country,
        "achievement_percent": str(certificate.achievement_percent),
        "completed_at": certificate.completed_at.isoformat() if certificate.completed_at else None,
        "expires_at": certificate.expires_at.isoformat() if certificate.expires_at else None,
        "skills": certificate.skills_snapshot or [],
        "projects": certificate.projects_snapshot or [],
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _active_certificate(qs):
    for certificate in qs.order_by("-issued_at", "-id"):
        if certificate.effective_status == Certificate.Status.ACTIVE:
            return certificate
    return None


def _latest_certificate(qs):
    return qs.order_by("-issued_at", "-id").first()


def _record_event(certificate, event_type, actor=None, details=None):
    return CertificateEvent.objects.create(
        certificate=certificate,
        event_type=event_type,
        actor=actor,
        details=details or {},
    )


def _prepare_replaced_certificate(previous, actor=None):
    if not previous:
        return
    if previous.effective_status == Certificate.Status.EXPIRED and previous.status != Certificate.Status.EXPIRED:
        previous.status = Certificate.Status.EXPIRED
        previous.save(update_fields=["status"])
        _record_event(previous, CertificateEvent.EventType.EXPIRED, actor=actor)
    elif previous.effective_status == Certificate.Status.ACTIVE:
        previous.status = Certificate.Status.REVOKED
        previous.revoked_at = timezone.now()
        previous.revocation_reason = previous.revocation_reason or "Remplacé par une réémission."
        previous.save(update_fields=["status", "revoked_at", "revocation_reason"])
        _record_event(
            previous,
            CertificateEvent.EventType.REVOKED,
            actor=actor,
            details={"reason": previous.revocation_reason, "automatic": True},
        )


def _finalize_new_certificate(cert, actor=None, previous=None):
    cert.credential_digest = _credential_digest(cert)
    cert.save(update_fields=["credential_digest"])
    _record_event(
        cert,
        CertificateEvent.EventType.ISSUED,
        actor=actor,
        details={"supersedes": previous.certificate_number if previous else None},
    )
    if previous:
        _record_event(
            previous,
            CertificateEvent.EventType.REISSUED,
            actor=actor,
            details={
                "replacement_certificate_number": cert.certificate_number,
                "replacement_verification_code": str(cert.verification_code),
            },
        )
    try:
        from apps.notifications.services import queue_certificate_ready

        transaction.on_commit(lambda certificate_id=cert.id: queue_certificate_ready(certificate_id))
    except Exception:
        pass


@transaction.atomic
def issue_course_certificate(enrollment, issued_by=None, force=False, force_new=False, supersedes=None):
    enrollment = enrollment.__class__.objects.select_for_update().get(pk=enrollment.pk)
    course = enrollment.course
    eligibility = course_eligibility(enrollment)
    if not force and not eligibility["eligible"]:
        raise ValueError(eligibility["reason"] or "L'apprenant n'est pas encore éligible.")

    qs = Certificate.objects.filter(course_enrollment=enrollment)
    active = _active_certificate(qs)
    if active and not force_new:
        return active, False
    previous = supersedes or _latest_certificate(qs)
    if previous and not force_new:
        raise ValueError("Un certificat existe déjà pour cette inscription. Utilisez la réémission explicite.")

    if force_new:
        _prepare_replaced_certificate(previous, actor=issued_by)

    skills, projects = _course_evidence(enrollment)
    issuer = _issuer_snapshot()
    cert = Certificate(course_enrollment=enrollment, user=enrollment.user, supersedes=previous if force_new else None)
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
    cert.metadata = {
        "course_id": course.id,
        "enrollment_id": enrollment.id,
        "threshold": eligibility["threshold"],
        "evidence_version": 1,
    }
    cert.issuer_name = issuer["name"]
    cert.issuer_country = issuer["country"]
    cert.skills_snapshot = skills
    cert.projects_snapshot = projects
    cert.schema_version = 2
    cert.save()
    _finalize_new_certificate(cert, actor=issued_by, previous=previous if force_new else None)

    if not enrollment.certificate_issued:
        enrollment.certificate_issued = True
        enrollment.save(update_fields=["certificate_issued"])
    return cert, True


@transaction.atomic
def issue_formation_certificate(enrollment, issued_by=None, force=False, force_new=False, supersedes=None):
    enrollment = enrollment.__class__.objects.select_for_update().get(pk=enrollment.pk)
    formation = enrollment.formation
    eligibility = formation_eligibility(enrollment)
    if not force and not eligibility["eligible"]:
        raise ValueError(eligibility["reason"] or "L'apprenant n'est pas encore éligible.")

    qs = Certificate.objects.filter(formation_enrollment=enrollment)
    active = _active_certificate(qs)
    if active and not force_new:
        return active, False
    previous = supersedes or _latest_certificate(qs)
    if previous and not force_new:
        raise ValueError("Un certificat existe déjà pour cette inscription. Utilisez la réémission explicite.")

    if force_new:
        _prepare_replaced_certificate(previous, actor=issued_by)

    issuer = _issuer_snapshot()
    cert = Certificate(formation_enrollment=enrollment, user=enrollment.user, supersedes=previous if force_new else None)
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
    cert.metadata = {
        "formation_id": formation.id,
        "enrollment_id": enrollment.id,
        "threshold": eligibility["threshold"],
        "evidence_version": 1,
    }
    cert.issuer_name = issuer["name"]
    cert.issuer_country = issuer["country"]
    cert.skills_snapshot = []
    cert.projects_snapshot = []
    cert.schema_version = 2
    cert.save()
    _finalize_new_certificate(cert, actor=issued_by, previous=previous if force_new else None)

    if not enrollment.certificate_issued:
        enrollment.certificate_issued = True
        enrollment.save(update_fields=["certificate_issued"])
    return cert, True


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
