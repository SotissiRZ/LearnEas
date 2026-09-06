from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from decimal import Decimal

from django.db.models import Q, Count
from django.utils import timezone

from apps.catalog.models import Course, PDFProduct
from apps.enrollments.models import CourseEnrollment
from apps.formations.models import InteractiveFormation, FormationKind, MentorshipOffering
from apps.opportunities.models import EmployerProfile, CandidateProfile, Opportunity
from apps.opportunities.services import employer_has_talent_pool_access, match_opportunity_breakdown

SEARCH_TYPES = ("course", "formation", "pdf", "mentor", "opportunity", "company", "talent")
PUBLIC_TYPES = ("course", "formation", "pdf", "mentor", "opportunity", "company")


def approved_employer_for(user):
    if not getattr(user, "is_authenticated", False) or getattr(user, "role", None) != "employer":
        return None
    return EmployerProfile.objects.filter(user=user, status=EmployerProfile.Status.APPROVED).first()


def normalize_text(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text.casefold()).strip()


def query_tokens(query: str) -> list[str]:
    normalized = normalize_text(query)[:120]
    return [token for token in re.findall(r"[\w+#.-]{2,}", normalized, flags=re.UNICODE) if len(token) >= 2][:8]


def db_query_tokens(query: str) -> list[str]:
    raw = str(query or "").strip()[:120]
    return [token for token in re.findall(r"[\w+#.-]{2,}", raw, flags=re.UNICODE) if len(token) >= 2][:8]


def parse_types(raw: str | None, *, allow_talents: bool) -> list[str]:
    allowed = set(SEARCH_TYPES if allow_talents else PUBLIC_TYPES)
    values = [part.strip().lower() for part in str(raw or "").split(",") if part.strip()]
    if values:
        return [value for value in values if value in allowed]
    return list(SEARCH_TYPES if allow_talents else PUBLIC_TYPES)


def _q_for(fields: Iterable[str], phrase: str, tokens: list[str]) -> Q:
    result = Q()
    if phrase:
        for field in fields:
            result |= Q(**{f"{field}__icontains": phrase})
    for token in tokens:
        for field in fields:
            result |= Q(**{f"{field}__icontains": token})
    return result


def _list_text(value: object) -> str:
    if isinstance(value, (list, tuple, set)):
        return " ".join(str(item) for item in value)
    return str(value or "")


def relevance_score(query: str, *, title: str, body: str = "", extras: Iterable[object] = (), boost: float = 0) -> float:
    phrase = normalize_text(query)
    tokens = query_tokens(query)
    title_n = normalize_text(title)
    body_n = normalize_text(body)
    extra_n = normalize_text(" ".join(_list_text(value) for value in extras))
    score = float(boost)
    if phrase:
        if title_n == phrase:
            score += 120
        elif title_n.startswith(phrase):
            score += 80
        elif phrase in title_n:
            score += 55
        elif phrase in body_n:
            score += 24
        elif phrase in extra_n:
            score += 20
    for token in tokens:
        if token in title_n:
            score += 15
        if token in body_n:
            score += 5
        if token in extra_n:
            score += 7
    return round(score, 2)


def media_url(field) -> str | None:
    try:
        return field.url if field else None
    except Exception:
        return None


def money(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


def _sort(rows: list[dict], limit: int) -> list[dict]:
    rows.sort(key=lambda row: (row.get("score", 0), row.get("freshness", 0)), reverse=True)
    for row in rows:
        row.pop("freshness", None)
    return rows[:limit]


def _timestamp(value) -> float:
    try:
        return value.timestamp()
    except Exception:
        return 0


def _course_rows(query: str, limit: int) -> list[dict]:
    tokens = db_query_tokens(query)
    phrase = str(query or "").strip()[:120]
    qs = Course.objects.filter(published=True).select_related("category", "category__domain", "instructor")
    if phrase:
        qs = qs.filter(_q_for(["title", "subtitle", "description", "what_you_will_learn", "requirements", "category__name", "category__domain__name"], phrase, tokens))
    rows = []
    for obj in qs.order_by("-featured", "-rating_avg", "-students_count", "-updated_at")[:80]:
        rows.append({
            "type": "course", "id": obj.id, "title": obj.title,
            "subtitle": obj.subtitle or (obj.category.name if obj.category else "Cours en ligne"),
            "description": obj.description[:260], "url": f"/courses/{obj.slug}", "image": media_url(obj.thumbnail),
            "score": relevance_score(query, title=obj.title, body=f"{obj.subtitle} {obj.description}", extras=[obj.category.name if obj.category else "", obj.what_you_will_learn], boost=(10 if obj.featured else 0) + min(float(obj.rating_avg or 0), 5)),
            "freshness": _timestamp(obj.updated_at),
            "meta": {"level": obj.level, "language": obj.language, "price": money(obj.discount_price or obj.price), "is_free": obj.is_free, "rating": float(obj.rating_avg or 0), "students": obj.students_count},
        })
    return _sort(rows, limit)


def _pdf_rows(query: str, limit: int) -> list[dict]:
    tokens = db_query_tokens(query); phrase = str(query or "").strip()[:120]
    qs = PDFProduct.objects.filter(published=True).select_related("category", "category__domain", "instructor")
    if phrase:
        qs = qs.filter(_q_for(["title", "description", "category__name", "category__domain__name"], phrase, tokens))
    rows = []
    for obj in qs.order_by("-featured", "-rating_avg", "-downloads_count", "-updated_at")[:80]:
        rows.append({
            "type": "pdf", "id": obj.id, "title": obj.title, "subtitle": obj.category.name if obj.category else "Ressource PDF",
            "description": obj.description[:260], "url": f"/pdfs/{obj.slug}", "image": media_url(obj.cover_image),
            "score": relevance_score(query, title=obj.title, body=obj.description, extras=[obj.category.name if obj.category else ""], boost=(10 if obj.featured else 0) + min(float(obj.rating_avg or 0), 5)),
            "freshness": _timestamp(obj.updated_at),
            "meta": {"level": obj.level, "language": obj.language, "price": money(obj.price), "is_free": obj.is_free, "pages": obj.page_count, "rating": float(obj.rating_avg or 0)},
        })
    return _sort(rows, limit)


def _formation_rows(query: str, limit: int) -> list[dict]:
    tokens = db_query_tokens(query); phrase = str(query or "").strip()[:120]
    qs = InteractiveFormation.objects.filter(published=True, kind=FormationKind.COHORT).select_related("category", "instructor").annotate(_students_count=Count("enrollments", filter=Q(enrollments__revoked_at__isnull=True), distinct=True))
    if phrase:
        qs = qs.filter(_q_for(["title", "description", "cohort_name", "category__name", "instructor__first_name", "instructor__last_name"], phrase, tokens))
    rows = []
    for obj in qs.order_by("-created_at")[:80]:
        rows.append({
            "type": "formation", "id": obj.id, "title": obj.title, "subtitle": obj.cohort_name or "Formation en direct",
            "description": obj.description[:260], "url": f"/formations/{obj.slug}", "image": media_url(obj.thumbnail),
            "score": relevance_score(query, title=obj.title, body=obj.description, extras=[obj.cohort_name, obj.category.name if obj.category else "", obj.instructor.get_full_name()], boost=4 if obj.status == "scheduled" else 0),
            "freshness": _timestamp(obj.updated_at),
            "meta": {"level": obj.level, "language": obj.language, "price": money(obj.price), "start_date": obj.start_date.isoformat() if obj.start_date else None, "seats_left": obj.seats_left},
        })
    return _sort(rows, limit)


def _mentor_rows(query: str, limit: int) -> list[dict]:
    tokens = db_query_tokens(query); phrase = str(query or "").strip()[:120]
    qs = MentorshipOffering.objects.filter(published=True).select_related("instructor")
    if phrase:
        qs = qs.filter(_q_for(["title", "description", "instructor__first_name", "instructor__last_name", "instructor__headline", "instructor__domain"], phrase, tokens))
    rows = []
    for obj in qs.order_by("-updated_at")[:80]:
        rows.append({
            "type": "mentor", "id": obj.id, "title": obj.title,
            "subtitle": obj.instructor.get_full_name() or obj.instructor.username, "description": obj.description[:260],
            "url": f"/mentorship/{obj.slug}", "image": media_url(obj.instructor.avatar),
            "score": relevance_score(query, title=obj.title, body=obj.description, extras=[obj.instructor.headline, obj.instructor.domain, obj.instructor.get_full_name()]),
            "freshness": _timestamp(obj.updated_at),
            "meta": {"duration_minutes": obj.duration_minutes, "price": money(obj.price), "language": obj.language, "timezone": obj.timezone},
        })
    return _sort(rows, limit)


def _opportunity_rows(query: str, limit: int, *, user=None) -> list[dict]:
    tokens = db_query_tokens(query); phrase = str(query or "").strip()[:120]; now = timezone.now()
    qs = Opportunity.objects.filter(status=Opportunity.Status.PUBLISHED).filter(Q(application_deadline__isnull=True) | Q(application_deadline__gt=now)).select_related("employer")
    if phrase:
        qs = qs.filter(_q_for(["title", "description", "department", "skills_required", "skills_optional", "country", "city", "employer__company_name", "employer__industry"], phrase, tokens))
    profile = None
    if user and getattr(user, "is_authenticated", False):
        try: profile = user.candidate_profile
        except CandidateProfile.DoesNotExist: profile = None
    rows = []
    for obj in qs.order_by("-featured", "-published_at")[:100]:
        match = None
        if profile:
            try: match = match_opportunity_breakdown(obj, user, profile=profile)["total"]
            except Exception: match = None
        rows.append({
            "type": "opportunity", "id": obj.id, "title": obj.title, "subtitle": obj.employer.company_name,
            "description": obj.description[:260], "url": f"/opportunities/{obj.slug}", "image": media_url(obj.cover_image) or media_url(obj.employer.logo),
            "score": relevance_score(query, title=obj.title, body=obj.description, extras=[obj.department, obj.country, obj.city, obj.skills_required, obj.skills_optional, obj.employer.company_name], boost=(10 if obj.featured else 0) + ((match or 0) / 10)),
            "freshness": _timestamp(obj.published_at or obj.created_at),
            "meta": {"kind": obj.kind, "work_mode": obj.work_mode, "country": obj.country, "city": obj.city, "match_score": match, "salary_min": money(obj.salary_min) if obj.show_salary else None, "salary_max": money(obj.salary_max) if obj.show_salary else None, "salary_currency": obj.salary_currency if obj.show_salary else None},
        })
    return _sort(rows, limit)


def _company_rows(query: str, limit: int) -> list[dict]:
    tokens = db_query_tokens(query); phrase = str(query or "").strip()[:120]; now = timezone.now()
    qs = EmployerProfile.objects.filter(status=EmployerProfile.Status.APPROVED).annotate(
        open_jobs=Count("opportunities", filter=Q(opportunities__status=Opportunity.Status.PUBLISHED) & (Q(opportunities__application_deadline__isnull=True) | Q(opportunities__application_deadline__gt=now)), distinct=True)
    )
    if phrase:
        qs = qs.filter(_q_for(["company_name", "tagline", "description", "industry", "country", "city"], phrase, tokens))
    rows = []
    for obj in qs.order_by("-open_jobs", "company_name")[:80]:
        verified = obj.verification_status == EmployerProfile.VerificationStatus.VERIFIED
        rows.append({
            "type": "company", "id": obj.id, "title": obj.company_name, "subtitle": obj.tagline or obj.industry or "Entreprise",
            "description": obj.description[:260], "url": f"/companies/{obj.slug}", "image": media_url(obj.logo),
            "score": relevance_score(query, title=obj.company_name, body=f"{obj.tagline} {obj.description}", extras=[obj.industry, obj.country, obj.city], boost=(12 if verified else 0) + min(int(obj.open_jobs or 0), 8)),
            "freshness": _timestamp(obj.updated_at),
            "meta": {"industry": obj.industry, "country": obj.country, "city": obj.city, "verified": verified, "open_jobs": int(obj.open_jobs or 0)},
        })
    return _sort(rows, limit)


def _talent_rows(query: str, limit: int, *, user) -> list[dict]:
    employer = approved_employer_for(user) if user and getattr(user, "is_authenticated", False) else None
    if not employer or not employer_has_talent_pool_access(employer):
        return []
    tokens = db_query_tokens(query); phrase = str(query or "").strip()[:120]
    qs = CandidateProfile.objects.filter(is_searchable=True).select_related("user")
    if phrase:
        qs = qs.filter(_q_for(["headline", "summary", "skills", "desired_roles", "user__first_name", "user__last_name", "user__country"], phrase, tokens))
    rows = []
    for obj in qs.order_by("-updated_at")[:100]:
        name = obj.user.get_full_name() or obj.user.username
        portfolio_slug = ""
        try:
            if obj.user.portfolio_profile.is_public: portfolio_slug = obj.user.portfolio_profile.slug
        except Exception:
            pass
        rows.append({
            "type": "talent", "id": obj.id, "title": name, "subtitle": obj.headline or "Talent KalanPro",
            "description": obj.summary[:260], "url": "/dashboard/employer", "image": media_url(obj.user.avatar),
            "score": relevance_score(query, title=name, body=f"{obj.headline} {obj.summary}", extras=[obj.skills, obj.desired_roles, obj.user.country, obj.availability]),
            "freshness": _timestamp(obj.updated_at),
            "meta": {"country": obj.user.country, "skills": list(obj.skills or [])[:8], "availability": obj.availability, "years_experience": obj.years_experience, "portfolio_slug": portfolio_slug, "talent_id": obj.id},
        })
    return _sort(rows, limit)


def search_all(*, query: str, types: list[str], limit: int, user=None) -> dict:
    funcs = {
        "course": lambda: _course_rows(query, limit), "formation": lambda: _formation_rows(query, limit),
        "pdf": lambda: _pdf_rows(query, limit), "mentor": lambda: _mentor_rows(query, limit),
        "opportunity": lambda: _opportunity_rows(query, limit, user=user), "company": lambda: _company_rows(query, limit),
        "talent": lambda: _talent_rows(query, limit, user=user),
    }
    groups = {kind: funcs[kind]() for kind in types if kind in funcs}
    merged = [row for kind in types for row in groups.get(kind, [])]
    merged.sort(key=lambda row: row.get("score", 0), reverse=True)
    return {"query": query, "types": types, "count": len(merged), "groups": groups, "results": merged[: max(limit * 3, limit)]}


def _profile_terms(user) -> list[str]:
    terms: list[str] = []
    if not user or not getattr(user, "is_authenticated", False):
        return terms
    terms.extend([getattr(user, "headline", ""), getattr(user, "domain", ""), getattr(user, "country", "")])
    try:
        profile = user.candidate_profile
        terms.extend([profile.headline, *list(profile.skills or []), *list(profile.desired_roles or []), *list(profile.preferred_countries or [])])
    except CandidateProfile.DoesNotExist:
        pass
    try:
        category_names = CourseEnrollment.objects.filter(user=user).select_related("course__category").values_list("course__category__name", flat=True)[:12]
        terms.extend([value for value in category_names if value])
    except Exception:
        pass
    cleaned = []
    seen = set()
    for value in terms:
        text = str(value or "").strip()
        key = normalize_text(text)
        if key and key not in seen:
            seen.add(key); cleaned.append(text)
    return cleaned[:20]


def recommendations_for(user, *, limit: int = 6) -> dict:
    terms = _profile_terms(user)
    query = " ".join(terms[:8])
    # Les helpers sont volontairement réutilisés : même politique de visibilité et même format.
    learning = _course_rows(query, limit) + _formation_rows(query, limit) + _pdf_rows(query, limit) + _mentor_rows(query, limit)
    learning.sort(key=lambda row: row.get("score", 0), reverse=True)
    learning = learning[:limit]
    opportunities = _opportunity_rows(query, limit, user=user)

    talents: list[dict] = []
    employer = approved_employer_for(user) if user and getattr(user, "is_authenticated", False) else None
    if employer and employer_has_talent_pool_access(employer):
        own_job = employer.opportunities.filter(status=Opportunity.Status.PUBLISHED).order_by("-published_at", "-id").first()
        if own_job:
            scored = []
            for talent in CandidateProfile.objects.filter(is_searchable=True).select_related("user").order_by("-updated_at")[:150]:
                breakdown = match_opportunity_breakdown(own_job, talent.user, profile=talent)
                if breakdown["total"] > 0:
                    scored.append((breakdown["total"], talent))
            scored.sort(key=lambda item: (item[0], item[1].updated_at), reverse=True)
            for score, talent in scored[:limit]:
                name = talent.user.get_full_name() or talent.user.username
                talents.append({
                    "type": "talent", "id": talent.id, "title": name, "subtitle": talent.headline or "Talent KalanPro",
                    "description": talent.summary[:260], "url": "/dashboard/employer", "image": media_url(talent.user.avatar), "score": score,
                    "meta": {"match_score": score, "opportunity_id": own_job.id, "opportunity_title": own_job.title, "skills": list(talent.skills or [])[:8], "talent_id": talent.id},
                    "reason": f"Correspond à « {own_job.title} »",
                })

    reason = "Basé sur votre profil et votre activité" if terms else "Sélection populaire et récente"
    for row in learning + opportunities:
        row["reason"] = reason
    return {"personalized": bool(terms), "signals": terms[:8], "learning": learning, "opportunities": opportunities, "talents": talents}


def suggestions(query: str, *, limit: int = 8, user=None) -> list[dict]:
    if len(normalize_text(query)) < 2:
        return []
    data = search_all(query=query, types=parse_types(None, allow_talents=False), limit=3, user=user)
    seen = set(); output = []
    for row in data["results"]:
        key = (row["type"], normalize_text(row["title"]))
        if key in seen: continue
        seen.add(key)
        output.append({"type": row["type"], "title": row["title"], "subtitle": row.get("subtitle", ""), "url": row["url"]})
        if len(output) >= limit: break
    return output
