from __future__ import annotations

from decimal import Decimal
import json
from django.db import models
from django.utils import timezone


def clean_strings(value, *, max_items=40, max_length=100):
    if value in (None, ""):
        return []
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except Exception:
            value = [part.strip() for part in value.split(",") if part.strip()]
    if not isinstance(value, list):
        raise ValueError("Une liste est attendue.")
    result = []
    seen = set()
    for item in value:
        text = " ".join(str(item or "").strip().split())[:max_length]
        key = text.casefold()
        if text and key not in seen:
            result.append(text)
            seen.add(key)
        if len(result) >= max_items:
            break
    return result


def normalize_skill(value):
    return " ".join(str(value or "").strip().casefold().replace("-", " ").replace("_", " ").split())


def candidate_skills_for(user, profile=None):
    skills = []
    if profile:
        skills.extend(profile.skills or [])
    try:
        portfolio = user.portfolio_profile
        skills.extend(portfolio.skills or [])
    except Exception:
        pass
    try:
        for item in user.portfolio_items.filter(is_verified=True):
            skills.extend(item.skills or [])
    except Exception:
        pass
    try:
        now = timezone.now()
        certs = user.certificates.filter(status="active").filter(
            models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now)
        ).only("skills_snapshot")[:20]
        for certificate in certs:
            skills.extend(certificate.skills_snapshot or [])
    except Exception:
        pass
    unique = []
    seen = set()
    for skill in skills:
        text = " ".join(str(skill or "").strip().split())[:100]
        key = normalize_skill(text)
        if text and key and key not in seen:
            unique.append(text)
            seen.add(key)
    return unique[:60]


def match_opportunity(opportunity, user, profile=None, candidate_skills=None):
    """Score explicable (0–100) : compétences, métier visé, mobilité et expérience."""
    if profile is None:
        try:
            profile = user.candidate_profile
        except Exception:
            profile = None

    source_skills = candidate_skills if candidate_skills is not None else candidate_skills_for(user, profile)
    candidate_skills = {normalize_skill(s) for s in source_skills if normalize_skill(s)}
    required = {normalize_skill(s) for s in (opportunity.skills_required or []) if normalize_skill(s)}
    optional = {normalize_skill(s) for s in (opportunity.skills_optional or []) if normalize_skill(s)}

    score = Decimal("0")
    # Les compétences restent le facteur principal du matching.
    if required:
        score += Decimal("55") * Decimal(len(required & candidate_skills)) / Decimal(len(required))
    else:
        score += Decimal("40")
    if optional:
        score += Decimal("10") * Decimal(len(optional & candidate_skills)) / Decimal(len(optional))
    else:
        score += Decimal("5")

    if profile:
        desired = [normalize_skill(role) for role in (profile.desired_roles or []) if normalize_skill(role)]
        title = normalize_skill(opportunity.title)
        if not desired:
            score += Decimal("5")
        elif any(role in title or title in role for role in desired):
            score += Decimal("10")
        elif any(token in title.split() for role in desired for token in role.split() if len(token) >= 4):
            score += Decimal("6")

        if not profile.preferred_work_modes or opportunity.work_mode in profile.preferred_work_modes:
            score += Decimal("8")
        if opportunity.remote_worldwide or not profile.preferred_countries or opportunity.country in profile.preferred_countries:
            score += Decimal("7")
        if not profile.preferred_kinds or opportunity.kind in profile.preferred_kinds:
            score += Decimal("5")

        experience_floor = {"entry": 0, "junior": 1, "mid": 3, "senior": 5, "lead": 7}.get(opportunity.experience_level, 0)
        years = int(profile.years_experience or 0)
        if years >= experience_floor:
            score += Decimal("5")
        elif years + 1 >= experience_floor:
            score += Decimal("3")
    else:
        # Sans profil candidat, on ne prétend pas connaître l'adéquation métier.
        if opportunity.remote_worldwide or not opportunity.country or opportunity.country == getattr(user, "country", ""):
            score += Decimal("7")

    return max(0, min(100, int(round(score))))


def build_application_snapshot(user, opportunity, *, share_portfolio=True):
    from apps.enrollments.models import Certificate

    try:
        profile = user.candidate_profile
    except Exception:
        profile = None
    skills = candidate_skills_for(user, profile)
    portfolio_data = {}
    verified_projects = []
    if share_portfolio:
        try:
            portfolio = user.portfolio_profile
            portfolio_data = {
                "slug": portfolio.slug,
                "title": portfolio.title,
                "about": portfolio.about,
                "skills": portfolio.skills or [],
                "is_public": bool(portfolio.is_public),
            }
            for item in user.portfolio_items.filter(is_verified=True).order_by("-verified_at", "-updated_at")[:20]:
                verified_projects.append({
                    "title": item.title,
                    "course": item.verified_course_title,
                    "assignment": item.verified_assignment_title,
                    "instructor": item.verified_instructor_name,
                    "score": str(item.verified_score) if item.verified_score is not None else None,
                    "max_score": item.verified_max_score,
                    "verified_at": item.verified_at.isoformat() if item.verified_at else None,
                    "skills": item.skills or [],
                })
        except Exception:
            pass

    now = timezone.now()
    cert_qs = Certificate.objects.filter(user=user, status=Certificate.Status.ACTIVE).filter(
        models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now)
    ).order_by("-issued_at")[:20]
    certificates = [{
        "number": cert.certificate_number,
        "verification_code": str(cert.verification_code),
        "title": cert.content_title,
        "skills": cert.skills_snapshot or [],
        "issued_at": cert.issued_at.isoformat(),
    } for cert in cert_qs]

    return {
        "candidate_name_snapshot": user.get_full_name() or user.username,
        "candidate_email_snapshot": user.email,
        "country_snapshot": user.country or "",
        "headline_snapshot": (profile.headline if profile else "") or user.headline or "",
        "skills_snapshot": skills,
        "portfolio_snapshot": portfolio_data,
        "certificates_snapshot": certificates,
        "verified_projects_snapshot": verified_projects,
        "match_score": match_opportunity(opportunity, user, profile),
    }

