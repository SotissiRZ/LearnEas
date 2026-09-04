from __future__ import annotations

import json
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db.models import Q
from django.utils import timezone

from apps.catalog.models import Course, PDFProduct
from apps.enrollments.models import Certificate, CourseEnrollment, Wishlist
from apps.formations.models import InteractiveFormation, FormationKind
from apps.opportunities.models import Opportunity
from apps.opportunities.services import candidate_skills_for, match_opportunity

from .models import AIActionLog, AIDraft


READ_TOOLS = {
    "search_learning_catalog",
    "get_my_progress",
    "get_my_certificates",
    "search_opportunities",
    "get_my_instructor_content",
}
WRITE_TOOLS = {"add_course_to_wishlist", "save_quiz_draft", "save_course_outline_draft"}


def _tool(name: str, description: str, properties: dict, required: list[str] | None = None) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required or [],
                "additionalProperties": False,
            },
        },
    }


BASE_TOOL_DEFINITIONS = [
    _tool(
        "search_learning_catalog",
        "Cherche dans le catalogue public KalanPro des cours vidéo, PDF et cohortes live. Utiliser pour toute demande de recommandation ou recherche de formation.",
        {
            "query": {"type": "string", "description": "Mots-clés recherchés."},
            "kind": {"type": "string", "enum": ["any", "course", "pdf", "cohort"], "description": "Type de contenu."},
            "domain": {"type": "string", "description": "Domaine ou catégorie souhaité, optionnel."},
            "max_price": {"type": "number", "minimum": 0, "description": "Prix maximum en EUR, optionnel."},
            "limit": {"type": "integer", "minimum": 1, "maximum": 10},
        },
    ),
    _tool(
        "get_my_progress",
        "Retourne la progression d'apprentissage du compte connecté sur ses cours acquis.",
        {"limit": {"type": "integer", "minimum": 1, "maximum": 20}},
    ),
    _tool(
        "get_my_certificates",
        "Retourne les certificats actifs du compte connecté.",
        {"limit": {"type": "integer", "minimum": 1, "maximum": 20}},
    ),
    _tool(
        "search_opportunities",
        "Cherche les emplois, stages, freelances et missions publiés dans KalanPro et calcule le score de correspondance du compte connecté.",
        {
            "query": {"type": "string"},
            "kind": {"type": "string", "enum": ["any", "job", "internship", "freelance", "mission"]},
            "work_mode": {"type": "string", "enum": ["any", "remote", "hybrid", "onsite"]},
            "country": {"type": "string"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 10},
        },
    ),
    _tool(
        "add_course_to_wishlist",
        "Prépare l'ajout d'un cours publié à la liste de souhaits du compte connecté. Cette action DOIT être confirmée par l'utilisateur avant exécution.",
        {"course_id": {"type": "integer", "minimum": 1}},
        ["course_id"],
    ),
]

INSTRUCTOR_TOOL_DEFINITIONS = [
    _tool(
        "get_my_instructor_content",
        "Retourne les cours, PDF et cohortes appartenant à l'instructeur connecté, y compris les brouillons.",
        {"limit": {"type": "integer", "minimum": 1, "maximum": 20}},
    ),
    _tool(
        "save_quiz_draft",
        "Prépare l'enregistrement d'un quiz généré comme brouillon IA privé de l'instructeur. Ne publie rien. Confirmation utilisateur obligatoire.",
        {
            "title": {"type": "string"},
            "course_id": {"type": "integer", "minimum": 1},
            "questions": {
                "type": "array",
                "maxItems": 20,
                "items": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"},
                        "options": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 6},
                        "correct_answer": {"type": "string"},
                        "explanation": {"type": "string"},
                    },
                    "required": ["question", "options", "correct_answer"],
                    "additionalProperties": False,
                },
            },
        },
        ["title", "questions"],
    ),
    _tool(
        "save_course_outline_draft",
        "Prépare l'enregistrement d'un plan de cours comme brouillon IA privé de l'instructeur. Ne crée ni ne publie un cours réel. Confirmation utilisateur obligatoire.",
        {
            "title": {"type": "string"},
            "description": {"type": "string"},
            "sections": {
                "type": "array",
                "maxItems": 20,
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "lessons": {"type": "array", "items": {"type": "string"}, "maxItems": 20},
                    },
                    "required": ["title", "lessons"],
                    "additionalProperties": False,
                },
            },
        },
        ["title", "sections"],
    ),
]


def definitions_for(user) -> list[dict]:
    tools = list(BASE_TOOL_DEFINITIONS)
    if user.role in {"instructor", "admin"}:
        tools.extend(INSTRUCTOR_TOOL_DEFINITIONS)
    return tools


def _clamp_limit(value: Any, default=6, maximum=10) -> int:
    try:
        return min(max(int(value or default), 1), maximum)
    except (TypeError, ValueError):
        return default


def _price(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return max(parsed, Decimal("0"))


def search_learning_catalog(user, args: dict) -> dict:
    query = " ".join(str(args.get("query") or "").split())[:160]
    kind = str(args.get("kind") or "any")
    domain = " ".join(str(args.get("domain") or "").split())[:100]
    max_price = _price(args.get("max_price"))
    limit = _clamp_limit(args.get("limit"), 6, 10)
    items: list[dict] = []

    text_q = Q()
    if query:
        text_q = Q(title__icontains=query) | Q(description__icontains=query) | Q(category__name__icontains=query) | Q(category__domain__name__icontains=query)
    domain_q = Q()
    if domain:
        domain_q = Q(category__name__icontains=domain) | Q(category__domain__name__icontains=domain)

    if kind in {"any", "course"}:
        qs = Course.objects.filter(published=True).select_related("category__domain", "instructor").filter(text_q).filter(domain_q)
        if max_price is not None:
            qs = qs.filter(Q(is_free=True) | Q(discount_price__lte=max_price) | Q(discount_price__isnull=True, price__lte=max_price))
        for row in qs.order_by("-featured", "-rating_avg", "-students_count")[:limit]:
            effective_price = Decimal("0") if row.is_free else (row.discount_price if row.discount_price is not None else row.price)
            items.append({
                "type": "course", "id": row.id, "title": row.title, "path": f"/courses/{row.slug}",
                "price_eur": float(effective_price), "free": bool(row.is_free), "level": row.level,
                "category": row.category.name if row.category else "", "domain": row.category.domain.name if row.category and row.category.domain else "",
                "rating": float(row.rating_avg or 0), "students": row.students_count,
            })

    if kind in {"any", "pdf"}:
        qs = PDFProduct.objects.filter(published=True).select_related("category__domain", "instructor").filter(text_q).filter(domain_q)
        if max_price is not None:
            qs = qs.filter(Q(is_free=True) | Q(price__lte=max_price))
        for row in qs.order_by("-featured", "-rating_avg", "-downloads_count")[:limit]:
            items.append({
                "type": "pdf", "id": row.id, "title": row.title, "path": f"/pdfs/{row.slug}",
                "price_eur": float(Decimal("0") if row.is_free else row.price), "free": bool(row.is_free), "level": row.level,
                "category": row.category.name if row.category else "", "domain": row.category.domain.name if row.category and row.category.domain else "",
                "rating": float(row.rating_avg or 0), "downloads": row.downloads_count,
            })

    if kind in {"any", "cohort"}:
        formation_q = Q()
        if query:
            formation_q = Q(title__icontains=query) | Q(description__icontains=query) | Q(category__name__icontains=query) | Q(category__domain__name__icontains=query)
        formation_domain_q = Q()
        if domain:
            formation_domain_q = Q(category__name__icontains=domain) | Q(category__domain__name__icontains=domain)
        qs = InteractiveFormation.objects.filter(published=True, kind=FormationKind.COHORT).select_related("category__domain", "instructor").filter(formation_q).filter(formation_domain_q)
        if max_price is not None:
            qs = qs.filter(price__lte=max_price)
        for row in qs.order_by("start_date", "-created_at")[:limit]:
            items.append({
                "type": "cohort", "id": row.id, "title": row.title, "path": f"/formations/{row.slug}",
                "price_eur": float(row.price), "free": row.price == 0, "level": row.level,
                "category": row.category.name if row.category else "", "domain": row.category.domain.name if row.category and row.category.domain else "",
                "start_date": row.start_date.isoformat() if row.start_date else None, "seats_left": row.seats_left,
            })

    # Mélange raisonné : les contenus premium/featured arrivent déjà haut dans chaque type.
    return {"count": len(items[:limit]), "items": items[:limit]}


def get_my_progress(user, args: dict) -> dict:
    limit = _clamp_limit(args.get("limit"), 10, 20)
    rows = CourseEnrollment.objects.filter(user=user).select_related("course", "last_accessed_lesson").order_by("-purchased_at")[:limit]
    return {
        "items": [{
            "course_id": row.course_id, "title": row.course.title, "path": f"/courses/{row.course.slug}",
            "progress_percent": row.progress_percent, "completed": row.completed,
            "last_lesson": row.last_accessed_lesson.title if row.last_accessed_lesson else None,
        } for row in rows]
    }


def get_my_certificates(user, args: dict) -> dict:
    limit = _clamp_limit(args.get("limit"), 10, 20)
    rows = Certificate.objects.filter(user=user, status=Certificate.Status.ACTIVE).order_by("-issued_at")[:limit]
    return {
        "items": [{
            "id": row.id, "number": row.certificate_number, "title": row.content_title,
            "issued_at": row.issued_at.isoformat(), "verification_code": str(row.verification_code),
            "path": f"/certificates/verify/{row.verification_code}",
        } for row in rows]
    }


def search_opportunities(user, args: dict) -> dict:
    query = " ".join(str(args.get("query") or "").split())[:160]
    kind = str(args.get("kind") or "any")
    work_mode = str(args.get("work_mode") or "any")
    country = " ".join(str(args.get("country") or "").split())[:100]
    limit = _clamp_limit(args.get("limit"), 6, 10)
    now = timezone.now()
    qs = Opportunity.objects.filter(status=Opportunity.Status.PUBLISHED).filter(Q(application_deadline__isnull=True) | Q(application_deadline__gt=now)).select_related("employer")
    if query:
        qs = qs.filter(Q(title__icontains=query) | Q(description__icontains=query) | Q(employer__company_name__icontains=query) | Q(country__icontains=query) | Q(city__icontains=query))
    if kind != "any" and kind in dict(Opportunity.Kind.choices):
        qs = qs.filter(kind=kind)
    if work_mode != "any" and work_mode in dict(Opportunity.WorkMode.choices):
        qs = qs.filter(work_mode=work_mode)
    if country:
        qs = qs.filter(Q(country__icontains=country) | Q(remote_worldwide=True))
    try:
        profile = user.candidate_profile
    except Exception:
        profile = None
    skills = candidate_skills_for(user, profile)
    candidates = list(qs[:50])
    ranked = sorted(((match_opportunity(row, user, profile, skills), row) for row in candidates), key=lambda pair: (pair[0], bool(pair[1].featured), pair[1].published_at or pair[1].created_at), reverse=True)[:limit]
    return {
        "items": [{
            "id": row.id, "title": row.title, "company": row.employer.company_name, "path": f"/opportunities/{row.slug}",
            "kind": row.kind, "work_mode": row.work_mode, "country": row.country, "city": row.city,
            "match_score": score, "deadline": row.application_deadline.isoformat() if row.application_deadline else None,
        } for score, row in ranked]
    }


def get_my_instructor_content(user, args: dict) -> dict:
    if user.role not in {"instructor", "admin"}:
        raise PermissionError("Outil réservé aux instructeurs.")
    limit = _clamp_limit(args.get("limit"), 10, 20)
    return {
        "courses": [{"id": c.id, "title": c.title, "published": c.published, "path": f"/courses/{c.slug}"} for c in Course.objects.filter(instructor=user).order_by("-updated_at")[:limit]],
        "pdfs": [{"id": p.id, "title": p.title, "published": p.published, "path": f"/pdfs/{p.slug}"} for p in PDFProduct.objects.filter(instructor=user).order_by("-updated_at")[:limit]],
        "cohorts": [{"id": f.id, "title": f.title, "published": f.published, "status": f.status, "path": f"/formations/{f.slug}"} for f in InteractiveFormation.objects.filter(instructor=user, kind=FormationKind.COHORT).order_by("-updated_at")[:limit]],
    }


READ_DISPATCH = {
    "search_learning_catalog": search_learning_catalog,
    "get_my_progress": get_my_progress,
    "get_my_certificates": get_my_certificates,
    "search_opportunities": search_opportunities,
    "get_my_instructor_content": get_my_instructor_content,
}


def execute_read_tool(user, name: str, args: dict) -> dict:
    handler = READ_DISPATCH.get(name)
    if not handler:
        raise ValueError("Outil de lecture inconnu.")
    return handler(user, args or {})


def action_label(name: str, args: dict) -> str:
    if name == "add_course_to_wishlist":
        course = Course.objects.filter(pk=args.get("course_id"), published=True).only("title").first()
        return f"Ajouter « {course.title if course else 'ce cours'} » aux favoris"
    if name == "save_quiz_draft":
        return f"Enregistrer le quiz « {str(args.get('title') or 'Quiz IA')[:120]} »"
    if name == "save_course_outline_draft":
        return f"Enregistrer le plan « {str(args.get('title') or 'Plan de cours IA')[:120]} »"
    return "Confirmer l'action KalanPro AI"


def validate_write_tool(user, name: str, args: dict) -> dict:
    args = args or {}
    if name == "add_course_to_wishlist":
        try:
            course_id = int(args.get("course_id"))
        except (TypeError, ValueError):
            raise ValueError("Cours invalide.")
        course = Course.objects.filter(pk=course_id, published=True).first()
        if not course:
            raise ValueError("Cours publié introuvable.")
        return {"course_id": course.id}

    if user.role not in {"instructor", "admin"}:
        raise PermissionError("Action réservée aux instructeurs.")

    title = " ".join(str(args.get("title") or "").split())[:220]
    if not title:
        raise ValueError("Titre requis.")
    course = None
    if args.get("course_id"):
        try:
            course_id = int(args.get("course_id"))
        except (TypeError, ValueError):
            raise ValueError("Cours invalide.")
        course = Course.objects.filter(pk=course_id).first()
        if not course or (user.role != "admin" and course.instructor_id != user.id):
            raise PermissionError("Vous ne pouvez pas rattacher ce brouillon à ce cours.")

    if name == "save_quiz_draft":
        questions = args.get("questions")
        if not isinstance(questions, list) or not questions or len(questions) > 20:
            raise ValueError("Le quiz doit contenir entre 1 et 20 questions.")
        clean = []
        for raw in questions:
            if not isinstance(raw, dict):
                raise ValueError("Format de question invalide.")
            q = " ".join(str(raw.get("question") or "").split())[:600]
            options = [" ".join(str(x or "").split())[:300] for x in (raw.get("options") or []) if str(x or "").strip()]
            correct = " ".join(str(raw.get("correct_answer") or "").split())[:300]
            explanation = str(raw.get("explanation") or "").strip()[:1200]
            if not q or len(options) < 2 or correct not in options:
                raise ValueError("Chaque question doit avoir au moins 2 options et une bonne réponse présente dans les options.")
            clean.append({"question": q, "options": options[:6], "correct_answer": correct, "explanation": explanation})
        return {"title": title, "course_id": course.id if course else None, "questions": clean}

    if name == "save_course_outline_draft":
        sections = args.get("sections")
        if not isinstance(sections, list) or not sections or len(sections) > 20:
            raise ValueError("Le plan doit contenir entre 1 et 20 sections.")
        clean_sections = []
        for raw in sections:
            if not isinstance(raw, dict):
                raise ValueError("Format de section invalide.")
            section_title = " ".join(str(raw.get("title") or "").split())[:220]
            lessons = [" ".join(str(x or "").split())[:220] for x in (raw.get("lessons") or []) if str(x or "").strip()][:20]
            if not section_title or not lessons:
                raise ValueError("Chaque section doit avoir un titre et au moins une leçon.")
            clean_sections.append({"title": section_title, "lessons": lessons})
        return {"title": title, "description": str(args.get("description") or "").strip()[:4000], "sections": clean_sections}

    raise ValueError("Action IA inconnue.")


def create_action_proposal(user, conversation, message, name: str, args: dict) -> AIActionLog:
    if name not in WRITE_TOOLS:
        raise ValueError("Cet outil ne nécessite pas de confirmation.")
    clean = validate_write_tool(user, name, args)
    return AIActionLog.objects.create(
        user=user,
        conversation=conversation,
        message=message,
        tool_name=name,
        label=action_label(name, clean),
        request_payload=clean,
        expires_at=timezone.now() + timedelta(minutes=20),
    )


def serialize_action(action: AIActionLog) -> dict:
    return {
        "id": action.id,
        "token": str(action.confirmation_token),
        "tool": action.tool_name,
        "label": action.label,
        "status": action.status,
        "requires_confirmation": action.status == AIActionLog.Status.PROPOSED,
        "expires_at": action.expires_at.isoformat() if action.expires_at else None,
        "result": action.result_payload or {},
        "error": action.error or "",
    }


def execute_action(action: AIActionLog) -> dict:
    if action.status != AIActionLog.Status.PROPOSED:
        raise ValueError("Cette action a déjà été traitée.")
    if action.expires_at and action.expires_at <= timezone.now():
        action.status = AIActionLog.Status.FAILED
        action.error = "La confirmation a expiré. Demandez à KalanPro AI de préparer à nouveau l'action."
        action.save(update_fields=["status", "error"])
        raise ValueError(action.error)

    args = validate_write_tool(action.user, action.tool_name, action.request_payload)
    if action.tool_name == "add_course_to_wishlist":
        wishlist, created = Wishlist.objects.get_or_create(user=action.user, course_id=args["course_id"], defaults={"pdf_product": None})
        result = {"wishlist_id": wishlist.id, "created": created, "course_id": args["course_id"], "path": "/wishlist"}
    elif action.tool_name == "save_quiz_draft":
        draft = AIDraft.objects.create(user=action.user, kind=AIDraft.Kind.QUIZ, title=args["title"], course_id=args.get("course_id"), payload={"questions": args["questions"]})
        result = {"draft_id": draft.id, "kind": draft.kind, "title": draft.title}
    elif action.tool_name == "save_course_outline_draft":
        draft = AIDraft.objects.create(user=action.user, kind=AIDraft.Kind.COURSE_OUTLINE, title=args["title"], payload={"description": args.get("description", ""), "sections": args["sections"]})
        result = {"draft_id": draft.id, "kind": draft.kind, "title": draft.title}
    else:
        raise ValueError("Action IA inconnue.")

    action.status = AIActionLog.Status.EXECUTED
    action.result_payload = result
    action.error = ""
    action.executed_at = timezone.now()
    action.save(update_fields=["status", "result_payload", "error", "executed_at"])
    return result


def reject_action(action: AIActionLog) -> None:
    if action.status != AIActionLog.Status.PROPOSED:
        raise ValueError("Cette action a déjà été traitée.")
    action.status = AIActionLog.Status.REJECTED
    action.save(update_fields=["status"])


def parse_tool_arguments(raw: Any) -> dict:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        parsed = json.loads(str(raw))
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, TypeError, ValueError):
        return {}
