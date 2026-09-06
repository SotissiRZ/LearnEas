from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from .models import ProjectAssignment, ProjectSubmission, PortfolioItem, PortfolioProfile


def required_projects_status(enrollment):
    assignments = ProjectAssignment.objects.filter(
        course=enrollment.course, published=True, required_for_certificate=True
    ).order_by("order", "id")
    missing = []
    for assignment in assignments:
        submission = ProjectSubmission.objects.filter(
            assignment=assignment, student=enrollment.user, status=ProjectSubmission.Status.APPROVED
        ).only("id").first()
        if not submission:
            missing.append(assignment)
    return {
        "required": assignments.count(),
        "completed": assignments.count() - len(missing),
        "complete": not missing,
        "missing": missing,
    }


def refresh_enrollment_after_project(enrollment):
    """Synchronise l'état terminé et le certificat après une validation de projet."""
    status = required_projects_status(enrollment)
    ready = int(enrollment.progress_percent or 0) >= 100 and status["complete"]
    changed = False
    if ready and not enrollment.completed:
        enrollment.completed = True
        enrollment.completed_at = timezone.now()
        changed = True
    if not ready and enrollment.completed and not enrollment.certificate_issued:
        # On n'invalide jamais silencieusement un certificat déjà émis.
        enrollment.completed = False
        enrollment.completed_at = None
        changed = True
    if changed:
        enrollment.save(update_fields=["completed", "completed_at"])

    if enrollment.course.certificate_enabled and enrollment.course.certificate_auto_issue:
        from apps.enrollments.certificates import course_eligibility, issue_course_certificate
        eligibility = course_eligibility(enrollment)
        if eligibility["eligible"]:
            issue_course_certificate(enrollment, issued_by=enrollment.course.instructor)
            enrollment.refresh_from_db()
    return enrollment


def ensure_portfolio_profile(user):
    base = (user.username or f"user-{user.id}").strip().lower()
    from django.utils.text import slugify
    base = slugify(base)[:85] or f"user-{user.id}"
    slug = base
    n = 1
    while PortfolioProfile.objects.filter(slug=slug).exclude(user=user).exists():
        n += 1
        slug = f"{base}-{n}"
    profile, _ = PortfolioProfile.objects.get_or_create(user=user, defaults={"slug": slug})
    return profile


@transaction.atomic
def publish_verified_submission(submission: ProjectSubmission):
    if submission.status != ProjectSubmission.Status.APPROVED:
        raise ValueError("Seul un projet validé peut être publié dans le portfolio.")
    ensure_portfolio_profile(submission.student)
    instructor = submission.assignment.course.instructor
    instructor_name = instructor.get_full_name() or instructor.username
    defaults = {
        "owner": submission.student,
        "title": submission.title or submission.assignment.title,
        "description": submission.summary,
        "external_url": submission.external_url,
        "repository_url": submission.repository_url,
        "skills": submission.skills or submission.assignment.skills or [],
        "stack": submission.skills or submission.assignment.skills or [],
        "is_public": True,
        "is_verified": True,
        "verified_course_title": submission.assignment.course.title,
        "verified_assignment_title": submission.assignment.title,
        "verified_instructor_name": instructor_name,
        "verified_at": submission.reviewed_at or timezone.now(),
        "verified_score": submission.score,
        "verified_max_score": submission.assignment.max_score,
    }
    item, _ = PortfolioItem.objects.update_or_create(source_submission=submission, defaults=defaults)
    if submission.cover_image:
        item.cover_image.name = submission.cover_image.name
        item.save(update_fields=["cover_image", "updated_at"])
    return item
