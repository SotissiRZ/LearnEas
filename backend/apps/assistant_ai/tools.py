from __future__ import annotations

import io
import json
import re
import zipfile
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from pypdf import PdfReader

from apps.catalog.models import Category, Course, Lesson, PDFProduct, Section
from apps.enrollments.models import Certificate, CourseEnrollment, Wishlist
from apps.formations.models import InteractiveFormation, FormationKind, MentorshipBooking, MentorshipOffering
from apps.opportunities.models import CandidateProfile, EmployerProfile, Opportunity, OpportunityApplication
from apps.opportunities.services import build_application_snapshot, candidate_skills_for, match_opportunity

from .models import AIActionLog, AIDraft


READ_TOOLS = {
    "search_learning_catalog",
    "get_my_progress",
    "get_my_certificates",
    "search_opportunities",
    "analyze_my_cv_against_opportunity",
    "get_my_instructor_content",
    "get_my_mentor_sessions",
    "get_my_recruiter_applications",
    "analyze_candidate_application",
    "recommend_learning_for_opportunity",
}
WRITE_TOOLS = {
    "add_course_to_wishlist",
    "save_quiz_draft",
    "save_course_outline_draft",
    "create_course_draft",
    "submit_opportunity_application",
    "save_mentorship_plan_draft",
    "save_interview_rubric_draft",
    "update_application_stage",
    "save_cv_improvement_draft",
    "save_cover_letter_draft",
    "save_learning_gap_plan_draft",
    "save_candidate_interview_prep_draft",
}


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
        "analyze_my_cv_against_opportunity",
        "Analyse le profil candidat et, si disponible, le CV du compte connecté face à une opportunité KalanPro précise. Retourne score, compétences correspondantes/manquantes et extrait CV sans candidater.",
        {"opportunity_id": {"type": "integer", "minimum": 1}},
        ["opportunity_id"],
    ),
    _tool(
        "submit_opportunity_application",
        "Prépare une candidature interne KalanPro avec lettre de motivation et portfolio. Cette action crée réellement la candidature uniquement après confirmation explicite de l'utilisateur.",
        {
            "opportunity_id": {"type": "integer", "minimum": 1},
            "cover_letter": {"type": "string", "description": "Lettre de motivation proposée, maximum 5000 caractères."},
            "share_portfolio": {"type": "boolean"},
        },
        ["opportunity_id"],
    ),

    _tool(
        "recommend_learning_for_opportunity",
        "À partir d'une opportunité KalanPro et du profil candidat connecté, identifie les compétences requises manquantes et recommande des cours/PDF/cohortes publiés pour les combler. Lecture seule.",
        {
            "opportunity_id": {"type": "integer", "minimum": 1},
            "limit": {"type": "integer", "minimum": 1, "maximum": 12},
            "max_price": {"type": "number", "minimum": 0},
        },
        ["opportunity_id"],
    ),
    _tool(
        "save_cv_improvement_draft",
        "Prépare une version améliorée du positionnement CV/profil du candidat, éventuellement ciblée sur une opportunité. N'écrase jamais le CV ni le profil. Enregistrement seulement après confirmation.",
        {
            "title": {"type": "string"},
            "opportunity_id": {"type": "integer", "minimum": 1},
            "professional_headline": {"type": "string"},
            "summary": {"type": "string"},
            "skills": {"type": "array", "items": {"type": "string"}, "maxItems": 30},
            "achievement_rewrites": {"type": "array", "items": {"type": "string"}, "maxItems": 20},
            "recommendations": {"type": "array", "items": {"type": "string"}, "maxItems": 20},
        },
        ["title", "professional_headline", "summary"],
    ),
    _tool(
        "save_cover_letter_draft",
        "Prépare une lettre de motivation ciblée sur une opportunité KalanPro et l'enregistre comme brouillon privé uniquement après confirmation. N'envoie pas de candidature.",
        {
            "opportunity_id": {"type": "integer", "minimum": 1},
            "title": {"type": "string"},
            "content": {"type": "string"},
            "key_points": {"type": "array", "items": {"type": "string"}, "maxItems": 10},
        },
        ["opportunity_id", "title", "content"],
    ),
    _tool(
        "save_learning_gap_plan_draft",
        "Enregistre après confirmation un plan privé pour combler les compétences manquantes face à une opportunité, avec étapes et contenus KalanPro recommandés.",
        {
            "opportunity_id": {"type": "integer", "minimum": 1},
            "title": {"type": "string"},
            "missing_skills": {"type": "array", "items": {"type": "string"}, "maxItems": 20},
            "actions": {
                "type": "array", "maxItems": 20,
                "items": {
                    "type": "object",
                    "properties": {
                        "skill": {"type": "string"},
                        "action": {"type": "string"},
                        "content_type": {"type": "string", "enum": ["course", "pdf", "cohort", "practice", "other"]},
                        "content_id": {"type": "integer", "minimum": 1},
                        "path": {"type": "string"},
                    },
                    "required": ["skill", "action"], "additionalProperties": False
                }
            },
        },
        ["opportunity_id", "title", "missing_skills", "actions"],
    ),
    _tool(
        "save_candidate_interview_prep_draft",
        "Prépare un plan privé d'entretien pour le candidat face à une opportunité KalanPro. Enregistrement après confirmation; aucun message n'est envoyé au recruteur.",
        {
            "opportunity_id": {"type": "integer", "minimum": 1},
            "title": {"type": "string"},
            "pitch": {"type": "string"},
            "likely_questions": {"type": "array", "items": {"type": "string"}, "maxItems": 15},
            "star_examples": {"type": "array", "items": {"type": "string"}, "maxItems": 10},
            "questions_to_ask": {"type": "array", "items": {"type": "string"}, "maxItems": 10},
            "checklist": {"type": "array", "items": {"type": "string"}, "maxItems": 12},
        },
        ["opportunity_id", "title", "pitch"],
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
    _tool(
        "create_course_draft",
        "Prépare la création d'un vrai cours KalanPro en brouillon, avec sections et leçons textuelles. Le cours reste non publié jusqu'à validation manuelle de l'instructeur. Confirmation obligatoire.",
        {
            "title": {"type": "string"},
            "subtitle": {"type": "string"},
            "description": {"type": "string"},
            "level": {"type": "string", "enum": ["beginner", "intermediate", "expert"]},
            "language": {"type": "string"},
            "category_id": {"type": "integer", "minimum": 1},
            "what_you_will_learn": {"type": "array", "items": {"type": "string"}, "maxItems": 12},
            "requirements": {"type": "array", "items": {"type": "string"}, "maxItems": 12},
            "target_audience": {"type": "array", "items": {"type": "string"}, "maxItems": 12},
            "sections": {
                "type": "array", "minItems": 1, "maxItems": 20,
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "lessons": {
                            "type": "array", "minItems": 1, "maxItems": 20,
                            "items": {
                                "type": "object",
                                "properties": {"title": {"type": "string"}, "description": {"type": "string"}},
                                "required": ["title"], "additionalProperties": False
                            }
                        },
                    },
                    "required": ["title", "lessons"], "additionalProperties": False
                }
            },
        },
        ["title", "description", "sections"],
    ),
]


MENTOR_TOOL_DEFINITIONS = [
    _tool(
        "get_my_mentor_sessions",
        "Retourne les prochaines séances de mentorat confirmées pour lesquelles le compte connecté est le mentor.",
        {"limit": {"type": "integer", "minimum": 1, "maximum": 20}},
    ),
    _tool(
        "save_mentorship_plan_draft",
        "Prépare l'enregistrement d'un plan privé de préparation de séance de mentorat. N'envoie rien au mentoré. Confirmation obligatoire.",
        {
            "booking_id": {"type": "integer", "minimum": 1},
            "title": {"type": "string"},
            "objectives": {"type": "array", "items": {"type": "string"}, "maxItems": 10},
            "agenda": {"type": "array", "items": {"type": "string"}, "maxItems": 12},
            "questions": {"type": "array", "items": {"type": "string"}, "maxItems": 12},
            "follow_up": {"type": "array", "items": {"type": "string"}, "maxItems": 10},
        },
        ["booking_id", "title"],
    ),
]

RECRUITER_TOOL_DEFINITIONS = [
    _tool(
        "get_my_recruiter_applications",
        "Retourne les candidatures reçues par l'entreprise approuvée du compte connecté. Peut filtrer par offre ou statut.",
        {
            "opportunity_id": {"type": "integer", "minimum": 1},
            "status": {"type": "string", "enum": ["any", "submitted", "reviewing", "shortlisted", "interview", "offer", "hired", "rejected", "withdrawn"]},
            "limit": {"type": "integer", "minimum": 1, "maximum": 30},
        },
    ),
    _tool(
        "analyze_candidate_application",
        "Analyse une candidature appartenant à l'entreprise du recruteur : adéquation compétences/offre, snapshot professionnel et points à vérifier. Lecture seule.",
        {"application_id": {"type": "integer", "minimum": 1}},
        ["application_id"],
    ),
    _tool(
        "save_interview_rubric_draft",
        "Prépare une grille d'entretien privée liée à une candidature. Ne contacte pas le candidat. Confirmation obligatoire.",
        {
            "application_id": {"type": "integer", "minimum": 1},
            "title": {"type": "string"},
            "criteria": {"type": "array", "items": {"type": "string"}, "maxItems": 12},
            "questions": {"type": "array", "items": {"type": "string"}, "maxItems": 15},
        },
        ["application_id", "title"],
    ),
    _tool(
        "update_application_stage",
        "Prépare le passage d'une candidature aux étapes étude, shortlist ou entretien. Ne permet pas de rejeter, embaucher ou faire une offre automatiquement. Confirmation obligatoire.",
        {
            "application_id": {"type": "integer", "minimum": 1},
            "status": {"type": "string", "enum": ["reviewing", "shortlisted", "interview"]},
            "recruiter_note": {"type": "string"},
        },
        ["application_id", "status"],
    ),
]

def _approved_employer_for(user):
    try:
        employer = user.employer_profile
    except Exception:
        return None
    return employer if employer.status == EmployerProfile.Status.APPROVED else None

def _is_mentor(user) -> bool:
    return user.role == "admin" or MentorshipOffering.objects.filter(instructor=user).exists()

def capabilities_for(user) -> list[str]:
    capabilities = ["learner"]
    if user.role in {"instructor", "admin"}:
        capabilities.append("instructor")
    if _is_mentor(user):
        capabilities.append("mentor")
    if user.role == "admin" or _approved_employer_for(user):
        capabilities.append("recruiter")
    if user.role == "admin":
        capabilities.append("admin")
    return capabilities


def definitions_for(user) -> list[dict]:
    tools = list(BASE_TOOL_DEFINITIONS)
    capabilities = set(capabilities_for(user))
    if "instructor" in capabilities:
        tools.extend(INSTRUCTOR_TOOL_DEFINITIONS)
    if "mentor" in capabilities:
        tools.extend(MENTOR_TOOL_DEFINITIONS)
    if "recruiter" in capabilities:
        tools.extend(RECRUITER_TOOL_DEFINITIONS)
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


def _normalized_skill(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().casefold())


def _extract_resume_excerpt(profile: CandidateProfile | None, max_chars: int = 6000) -> tuple[str, str]:
    if not profile or not profile.resume:
        return "", "Aucun CV n'est enregistré dans le profil candidat."
    try:
        name = str(profile.resume.name or "")
        suffix = Path(name).suffix.lower()
        profile.resume.open("rb")
        data = profile.resume.read(5 * 1024 * 1024 + 1)
        profile.resume.close()
        if len(data) > 5 * 1024 * 1024:
            return "", "CV trop volumineux pour l'analyse IA rapide."
        text = ""
        if suffix == ".pdf":
            reader = PdfReader(io.BytesIO(data))
            text = "\n".join((page.extract_text() or "") for page in reader.pages[:30])
        elif suffix == ".docx":
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                xml = archive.read("word/document.xml").decode("utf-8", errors="ignore")
            text = re.sub(r"<[^>]+>", " ", xml)
        else:
            return "", f"Extraction automatique non disponible pour le format {suffix or 'inconnu'}."
        text = re.sub(r"\s+", " ", text).strip()[:max_chars]
        return text, "CV analysé." if text else "Le CV ne contient pas de texte extractible."
    except Exception:
        try:
            profile.resume.close()
        except Exception:
            pass
        return "", "Le CV n'a pas pu être lu automatiquement."


def analyze_my_cv_against_opportunity(user, args: dict) -> dict:
    try:
        opportunity_id = int(args.get("opportunity_id"))
    except (TypeError, ValueError):
        raise ValueError("Opportunité invalide.")
    opportunity = Opportunity.objects.select_related("employer").filter(pk=opportunity_id, status=Opportunity.Status.PUBLISHED).first()
    if not opportunity or not opportunity.is_open or opportunity.employer.status != EmployerProfile.Status.APPROVED:
        raise ValueError("Opportunité publiée et ouverte introuvable.")
    try:
        profile = user.candidate_profile
    except Exception:
        profile = None
    candidate_skills = candidate_skills_for(user, profile)
    normalized = {_normalized_skill(skill): skill for skill in candidate_skills if _normalized_skill(skill)}
    required = [str(skill).strip() for skill in (opportunity.skills_required or []) if str(skill).strip()]
    optional = [str(skill).strip() for skill in (opportunity.skills_optional or []) if str(skill).strip()]
    matched_required = [skill for skill in required if _normalized_skill(skill) in normalized]
    missing_required = [skill for skill in required if _normalized_skill(skill) not in normalized]
    matched_optional = [skill for skill in optional if _normalized_skill(skill) in normalized]
    resume_excerpt, resume_note = _extract_resume_excerpt(profile)
    score = match_opportunity(opportunity, user, profile, candidate_skills)
    return {
        "opportunity": {
            "id": opportunity.id, "title": opportunity.title, "company": opportunity.employer.company_name,
            "path": f"/opportunities/{opportunity.slug}", "kind": opportunity.kind, "work_mode": opportunity.work_mode,
            "experience_level": opportunity.experience_level, "country": opportunity.country, "city": opportunity.city,
            "description": opportunity.description[:3500], "requirements": opportunity.requirements[:20],
            "responsibilities": opportunity.responsibilities[:20], "skills_required": required, "skills_optional": optional,
        },
        "candidate": {
            "headline": profile.headline if profile else getattr(user, "headline", ""),
            "summary": profile.summary[:2500] if profile else "",
            "years_experience": profile.years_experience if profile else getattr(user, "years_experience", 0),
            "skills": candidate_skills[:40],
            "desired_roles": (profile.desired_roles or [])[:20] if profile else [],
            "resume_excerpt": resume_excerpt, "resume_note": resume_note,
        },
        "analysis": {
            "match_score": score, "matched_required_skills": matched_required,
            "missing_required_skills": missing_required, "matched_optional_skills": matched_optional,
        },
    }


def recommend_learning_for_opportunity(user, args: dict) -> dict:
    analysis = analyze_my_cv_against_opportunity(user, args)
    missing = list(analysis.get("analysis", {}).get("missing_required_skills") or [])[:12]
    limit = _clamp_limit(args.get("limit"), 8, 12)
    max_price = _price(args.get("max_price"))
    seen: set[tuple[str, int]] = set()
    recommendations: list[dict] = []
    for skill in missing:
        result = search_learning_catalog(user, {
            "query": skill, "kind": "any", "domain": "", "max_price": max_price, "limit": min(4, limit),
        })
        for item in result.get("items", []):
            key = (str(item.get("type")), int(item.get("id") or 0))
            if key in seen or not key[1]:
                continue
            seen.add(key)
            recommendations.append({**item, "targets_skill": skill})
            if len(recommendations) >= limit:
                break
        if len(recommendations) >= limit:
            break
    return {
        "opportunity": analysis["opportunity"],
        "match_score": analysis.get("analysis", {}).get("match_score", 0),
        "missing_skills": missing,
        "recommendations": recommendations,
        "note": "Les recommandations proviennent du catalogue publié KalanPro et doivent être validées par l'utilisateur.",
    }


def get_my_mentor_sessions(user, args: dict) -> dict:
    if not _is_mentor(user):
        raise PermissionError("Outil réservé aux mentors.")
    limit = _clamp_limit(args.get("limit"), 8, 20)
    qs = MentorshipBooking.objects.select_related("user", "offering", "slot").filter(
        status=MentorshipBooking.Status.CONFIRMED, slot__starts_at__gte=timezone.now()
    )
    if user.role != "admin":
        qs = qs.filter(offering__instructor=user)
    return {"items": [{
        "booking_id": row.id, "offering": row.offering.title, "starts_at": row.slot.starts_at.isoformat(),
        "duration_minutes": row.offering.duration_minutes,
        "learner": row.user.get_full_name() or row.user.username,
        "learner_note": row.learner_note[:1500], "mentor_note": row.mentor_note[:1500],
        "session_id": row.join_session_id,
    } for row in qs.order_by("slot__starts_at")[:limit]]}


def _recruiter_application(user, application_id: int) -> OpportunityApplication:
    qs = OpportunityApplication.objects.select_related("candidate", "opportunity", "opportunity__employer")
    application = qs.filter(pk=application_id).first()
    if not application:
        raise ValueError("Candidature introuvable.")
    if user.role != "admin":
        employer = _approved_employer_for(user)
        if not employer or application.opportunity.employer_id != employer.id:
            raise PermissionError("Cette candidature n'appartient pas à votre entreprise.")
    return application


def get_my_recruiter_applications(user, args: dict) -> dict:
    employer = None if user.role == "admin" else _approved_employer_for(user)
    if user.role != "admin" and not employer:
        raise PermissionError("Profil recruteur approuvé requis.")
    limit = _clamp_limit(args.get("limit"), 12, 30)
    qs = OpportunityApplication.objects.select_related("candidate", "opportunity", "opportunity__employer")
    if employer:
        qs = qs.filter(opportunity__employer=employer)
    if args.get("opportunity_id"):
        try:
            qs = qs.filter(opportunity_id=int(args.get("opportunity_id")))
        except (TypeError, ValueError):
            raise ValueError("Opportunité invalide.")
    status_value = str(args.get("status") or "any")
    if status_value != "any" and status_value in dict(OpportunityApplication.Status.choices):
        qs = qs.filter(status=status_value)
    return {"items": [{
        "application_id": row.id, "opportunity_id": row.opportunity_id, "opportunity": row.opportunity.title,
        "candidate": row.candidate_name_snapshot, "headline": row.headline_snapshot, "skills": row.skills_snapshot[:30],
        "match_score": row.match_score, "status": row.status, "applied_at": row.applied_at.isoformat(),
    } for row in qs.order_by("-match_score", "-applied_at")[:limit]]}


def analyze_candidate_application(user, args: dict) -> dict:
    try:
        application_id = int(args.get("application_id"))
    except (TypeError, ValueError):
        raise ValueError("Candidature invalide.")
    row = _recruiter_application(user, application_id)
    required = [str(x).strip() for x in (row.opportunity.skills_required or []) if str(x).strip()]
    candidate = {_normalized_skill(x): x for x in (row.skills_snapshot or []) if _normalized_skill(x)}
    matched = [skill for skill in required if _normalized_skill(skill) in candidate]
    missing = [skill for skill in required if _normalized_skill(skill) not in candidate]
    return {
        "application": {
            "id": row.id, "status": row.status, "match_score": row.match_score,
            "candidate_name": row.candidate_name_snapshot, "headline": row.headline_snapshot,
            "country": row.country_snapshot, "skills": row.skills_snapshot[:40],
            "portfolio": row.portfolio_snapshot, "certificates": row.certificates_snapshot[:20],
            "verified_projects": row.verified_projects_snapshot[:20], "cover_letter": row.cover_letter[:5000],
            "path": "/dashboard/employer",
        },
        "opportunity": {
            "id": row.opportunity_id, "title": row.opportunity.title,
            "description": row.opportunity.description[:3500], "requirements": row.opportunity.requirements[:20],
            "skills_required": required, "skills_optional": row.opportunity.skills_optional[:20],
        },
        "analysis": {"matched_required_skills": matched, "missing_required_skills": missing},
    }


READ_DISPATCH = {
    "search_learning_catalog": search_learning_catalog,
    "get_my_progress": get_my_progress,
    "get_my_certificates": get_my_certificates,
    "search_opportunities": search_opportunities,
    "analyze_my_cv_against_opportunity": analyze_my_cv_against_opportunity,
    "get_my_instructor_content": get_my_instructor_content,
    "get_my_mentor_sessions": get_my_mentor_sessions,
    "get_my_recruiter_applications": get_my_recruiter_applications,
    "analyze_candidate_application": analyze_candidate_application,
    "recommend_learning_for_opportunity": recommend_learning_for_opportunity,
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
    if name == "submit_opportunity_application":
        opportunity = Opportunity.objects.filter(pk=args.get("opportunity_id")).only("title").first()
        return f"Envoyer ma candidature à « {opportunity.title if opportunity else 'cette offre'} »"
    if name == "save_quiz_draft":
        return f"Enregistrer le quiz « {str(args.get('title') or 'Quiz IA')[:120]} »"
    if name == "save_course_outline_draft":
        return f"Enregistrer le plan « {str(args.get('title') or 'Plan de cours IA')[:120]} »"
    if name == "create_course_draft":
        return f"Créer le cours brouillon « {str(args.get('title') or 'Cours IA')[:120]} »"
    if name == "save_mentorship_plan_draft":
        return f"Enregistrer le plan de mentorat « {str(args.get('title') or 'Préparation mentorat')[:120]} »"
    if name == "save_interview_rubric_draft":
        return f"Enregistrer la grille d’entretien « {str(args.get('title') or 'Entretien')[:120]} »"
    if name == "update_application_stage":
        labels = {"reviewing": "en étude", "shortlisted": "en shortlist", "interview": "en entretien"}
        return f"Passer la candidature #{args.get('application_id')} {labels.get(str(args.get('status')), '')}".strip()
    if name == "save_cv_improvement_draft":
        return f"Enregistrer l’amélioration CV « {str(args.get('title') or 'CV optimisé')[:120]} »"
    if name == "save_cover_letter_draft":
        return f"Enregistrer la lettre « {str(args.get('title') or 'Lettre de motivation')[:120]} »"
    if name == "save_learning_gap_plan_draft":
        return f"Enregistrer le plan de compétences « {str(args.get('title') or 'Plan de progression')[:120]} »"
    if name == "save_candidate_interview_prep_draft":
        return f"Enregistrer la préparation d’entretien « {str(args.get('title') or 'Préparation entretien')[:120]} »"
    return "Confirmer l'action KalanPro AI"


def _clean_string_list(values: Any, *, maximum: int = 12, item_max: int = 500) -> list[str]:
    if not isinstance(values, list):
        return []
    cleaned = []
    for value in values[:maximum]:
        text = " ".join(str(value or "").split())[:item_max]
        if text:
            cleaned.append(text)
    return cleaned


def _validate_application_submission(user, args: dict) -> dict:
    try:
        opportunity_id = int(args.get("opportunity_id"))
    except (TypeError, ValueError):
        raise ValueError("Opportunité invalide.")
    opportunity = Opportunity.objects.select_related("employer").filter(pk=opportunity_id).first()
    if not opportunity:
        raise ValueError("Opportunité introuvable.")
    if opportunity.apply_mode != Opportunity.ApplyMode.INTERNAL:
        raise ValueError("Cette opportunité utilise une candidature externe.")
    if opportunity.employer.user_id == user.id:
        raise PermissionError("Vous ne pouvez pas candidater à votre propre offre.")
    if not opportunity.is_open or opportunity.employer.status != EmployerProfile.Status.APPROVED:
        raise ValueError("Les candidatures sont clôturées pour cette opportunité.")
    if OpportunityApplication.objects.filter(opportunity=opportunity, candidate=user).exists():
        raise ValueError("Vous avez déjà candidaté à cette opportunité.")
    return {
        "opportunity_id": opportunity.id,
        "cover_letter": str(args.get("cover_letter") or "").strip()[:5000],
        "share_portfolio": bool(args.get("share_portfolio", True)),
    }


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

    if name == "submit_opportunity_application":
        return _validate_application_submission(user, args)

    if name == "update_application_stage":
        try:
            application_id = int(args.get("application_id"))
        except (TypeError, ValueError):
            raise ValueError("Candidature invalide.")
        application = _recruiter_application(user, application_id)
        allowed = {
            OpportunityApplication.Status.REVIEWING,
            OpportunityApplication.Status.SHORTLISTED,
            OpportunityApplication.Status.INTERVIEW,
        }
        new_status = str(args.get("status") or "")
        if new_status not in allowed:
            raise ValueError("Étape recruteur non autorisée par KalanPro AI.")
        if application.status in {
            OpportunityApplication.Status.WITHDRAWN,
            OpportunityApplication.Status.HIRED,
            OpportunityApplication.Status.REJECTED,
        }:
            raise ValueError("Cette candidature est dans un état final et ne peut plus être déplacée par l'assistant.")
        return {
            "application_id": application.id,
            "status": new_status,
            "recruiter_note": str(args.get("recruiter_note") or "").strip()[:5000],
        }

    if name == "save_interview_rubric_draft":
        try:
            application_id = int(args.get("application_id"))
        except (TypeError, ValueError):
            raise ValueError("Candidature invalide.")
        application = _recruiter_application(user, application_id)
        title = " ".join(str(args.get("title") or "").split())[:220]
        if not title:
            raise ValueError("Titre requis.")
        criteria = _clean_string_list(args.get("criteria"), maximum=12, item_max=500)
        questions = _clean_string_list(args.get("questions"), maximum=15, item_max=800)
        if not criteria and not questions:
            raise ValueError("Ajoutez au moins un critère ou une question d'entretien.")
        return {"application_id": application.id, "title": title, "criteria": criteria, "questions": questions}

    if name == "save_mentorship_plan_draft":
        try:
            booking_id = int(args.get("booking_id"))
        except (TypeError, ValueError):
            raise ValueError("Réservation de mentorat invalide.")
        booking = MentorshipBooking.objects.select_related("offering", "user", "slot").filter(pk=booking_id).first()
        if not booking:
            raise ValueError("Réservation de mentorat introuvable.")
        if user.role != "admin" and booking.offering.instructor_id != user.id:
            raise PermissionError("Cette séance ne vous appartient pas.")
        if booking.status != MentorshipBooking.Status.CONFIRMED:
            raise ValueError("Seules les séances confirmées peuvent recevoir un plan de préparation.")
        title = " ".join(str(args.get("title") or "").split())[:220]
        if not title:
            raise ValueError("Titre requis.")
        return {
            "booking_id": booking.id,
            "title": title,
            "objectives": _clean_string_list(args.get("objectives"), maximum=10, item_max=600),
            "agenda": _clean_string_list(args.get("agenda"), maximum=12, item_max=600),
            "questions": _clean_string_list(args.get("questions"), maximum=12, item_max=800),
            "follow_up": _clean_string_list(args.get("follow_up"), maximum=10, item_max=600),
        }

    if name == "save_cv_improvement_draft":
        title = " ".join(str(args.get("title") or "").split())[:220]
        headline = " ".join(str(args.get("professional_headline") or "").split())[:180]
        summary = str(args.get("summary") or "").strip()[:5000]
        if not title or not headline or not summary:
            raise ValueError("Titre, accroche professionnelle et résumé sont requis.")
        opportunity_id = None
        opportunity_title = ""
        if args.get("opportunity_id"):
            try:
                opportunity_id = int(args.get("opportunity_id"))
            except (TypeError, ValueError):
                raise ValueError("Opportunité invalide.")
            opportunity = Opportunity.objects.select_related("employer").filter(pk=opportunity_id, status=Opportunity.Status.PUBLISHED).first()
            if not opportunity or opportunity.employer.status != EmployerProfile.Status.APPROVED:
                raise ValueError("Opportunité publiée introuvable.")
            if opportunity.employer.user_id == user.id:
                raise PermissionError("Vous ne pouvez pas cibler votre propre offre comme candidat.")
            opportunity_title = opportunity.title
        return {
            "title": title, "opportunity_id": opportunity_id, "opportunity_title": opportunity_title,
            "professional_headline": headline, "summary": summary,
            "skills": _clean_string_list(args.get("skills"), maximum=30, item_max=120),
            "achievement_rewrites": _clean_string_list(args.get("achievement_rewrites"), maximum=20, item_max=700),
            "recommendations": _clean_string_list(args.get("recommendations"), maximum=20, item_max=700),
        }

    if name in {"save_cover_letter_draft", "save_learning_gap_plan_draft", "save_candidate_interview_prep_draft"}:
        try:
            opportunity_id = int(args.get("opportunity_id"))
        except (TypeError, ValueError):
            raise ValueError("Opportunité invalide.")
        opportunity = Opportunity.objects.select_related("employer").filter(pk=opportunity_id, status=Opportunity.Status.PUBLISHED).first()
        if not opportunity or opportunity.employer.status != EmployerProfile.Status.APPROVED:
            raise ValueError("Opportunité publiée introuvable.")
        if opportunity.employer.user_id == user.id:
            raise PermissionError("Cette action candidat ne peut pas cibler votre propre offre.")
        title = " ".join(str(args.get("title") or "").split())[:220]
        if not title:
            raise ValueError("Titre requis.")
        if name == "save_cover_letter_draft":
            content = str(args.get("content") or "").strip()[:7000]
            if not content:
                raise ValueError("Le contenu de la lettre est requis.")
            return {
                "opportunity_id": opportunity.id, "opportunity_title": opportunity.title, "title": title,
                "content": content, "key_points": _clean_string_list(args.get("key_points"), maximum=10, item_max=500),
            }
        if name == "save_learning_gap_plan_draft":
            missing = _clean_string_list(args.get("missing_skills"), maximum=20, item_max=120)
            raw_actions = args.get("actions") or []
            if not missing or not isinstance(raw_actions, list) or not raw_actions:
                raise ValueError("Ajoutez des compétences manquantes et au moins une action de progression.")
            clean_actions = []
            for raw in raw_actions[:20]:
                if not isinstance(raw, dict):
                    continue
                skill = " ".join(str(raw.get("skill") or "").split())[:120]
                action_text = str(raw.get("action") or "").strip()[:900]
                if not skill or not action_text:
                    continue
                content_type = str(raw.get("content_type") or "other")
                if content_type not in {"course", "pdf", "cohort", "practice", "other"}:
                    content_type = "other"
                content_id = raw.get("content_id")
                try:
                    content_id = int(content_id) if content_id else None
                except (TypeError, ValueError):
                    content_id = None
                path = str(raw.get("path") or "")[:500]
                clean_actions.append({"skill": skill, "action": action_text, "content_type": content_type, "content_id": content_id, "path": path})
            if not clean_actions:
                raise ValueError("Aucune action de progression valide.")
            return {
                "opportunity_id": opportunity.id, "opportunity_title": opportunity.title, "title": title,
                "missing_skills": missing, "actions": clean_actions,
            }
        pitch = str(args.get("pitch") or "").strip()[:3000]
        if not pitch:
            raise ValueError("Le pitch candidat est requis.")
        return {
            "opportunity_id": opportunity.id, "opportunity_title": opportunity.title, "title": title, "pitch": pitch,
            "likely_questions": _clean_string_list(args.get("likely_questions"), maximum=15, item_max=900),
            "star_examples": _clean_string_list(args.get("star_examples"), maximum=10, item_max=1400),
            "questions_to_ask": _clean_string_list(args.get("questions_to_ask"), maximum=10, item_max=900),
            "checklist": _clean_string_list(args.get("checklist"), maximum=12, item_max=500),
        }

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

    if name == "create_course_draft":
        description = str(args.get("description") or "").strip()[:12000]
        if not description:
            raise ValueError("Description du cours requise.")
        level = str(args.get("level") or "beginner")
        if level not in {"beginner", "intermediate", "expert"}:
            level = "beginner"
        category = None
        if args.get("category_id"):
            try:
                category = Category.objects.filter(pk=int(args.get("category_id"))).first()
            except (TypeError, ValueError):
                category = None
            if not category:
                raise ValueError("Catégorie introuvable.")
        sections = args.get("sections")
        if not isinstance(sections, list) or not sections or len(sections) > 20:
            raise ValueError("Le cours doit contenir entre 1 et 20 sections.")
        clean_sections = []
        for raw in sections:
            if not isinstance(raw, dict):
                raise ValueError("Format de section invalide.")
            section_title = " ".join(str(raw.get("title") or "").split())[:200]
            raw_lessons = raw.get("lessons") or []
            if not section_title or not isinstance(raw_lessons, list) or not raw_lessons or len(raw_lessons) > 20:
                raise ValueError("Chaque section doit avoir un titre et entre 1 et 20 leçons.")
            lessons = []
            for item in raw_lessons:
                if isinstance(item, dict):
                    lesson_title = " ".join(str(item.get("title") or "").split())[:200]
                    lesson_description = str(item.get("description") or "").strip()[:4000]
                else:
                    lesson_title = " ".join(str(item or "").split())[:200]
                    lesson_description = ""
                if not lesson_title:
                    raise ValueError("Titre de leçon invalide.")
                lessons.append({"title": lesson_title, "description": lesson_description})
            clean_sections.append({"title": section_title, "lessons": lessons})
        return {
            "title": title,
            "subtitle": " ".join(str(args.get("subtitle") or "").split())[:255],
            "description": description,
            "level": level,
            "language": " ".join(str(args.get("language") or "Français").split())[:50] or "Français",
            "category_id": category.id if category else None,
            "what_you_will_learn": _clean_string_list(args.get("what_you_will_learn"), maximum=12, item_max=500),
            "requirements": _clean_string_list(args.get("requirements"), maximum=12, item_max=500),
            "target_audience": _clean_string_list(args.get("target_audience"), maximum=12, item_max=500),
            "sections": clean_sections,
        }

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


def _copy_profile_resume(user):
    try:
        source = user.candidate_profile.resume
    except Exception:
        source = None
    if not source:
        return None
    try:
        if source.size > 10 * 1024 * 1024:
            return None
        source.open("rb")
        content = source.read()
        source.close()
        filename = Path(source.name).name or f"cv-{user.id}.pdf"
        return ContentFile(content, name=filename)
    except Exception:
        try:
            source.close()
        except Exception:
            pass
        return None


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

    elif action.tool_name == "submit_opportunity_application":
        with transaction.atomic():
            opportunity = Opportunity.objects.select_for_update().select_related("employer").get(pk=args["opportunity_id"])
            # Revalidation sous verrou : évite double-clics et candidatures après clôture.
            clean = _validate_application_submission(action.user, args)
            snapshot = build_application_snapshot(action.user, opportunity, share_portfolio=clean["share_portfolio"])
            application = OpportunityApplication(
                opportunity=opportunity,
                candidate=action.user,
                cover_letter=clean["cover_letter"],
                share_portfolio=clean["share_portfolio"],
                **snapshot,
            )
            resume_file = _copy_profile_resume(action.user)
            if resume_file:
                application.resume_file = resume_file
            application.save()
        result = {
            "application_id": application.id,
            "opportunity_id": opportunity.id,
            "status": application.status,
            "path": f"/opportunities/{opportunity.slug}",
        }

    elif action.tool_name == "save_cv_improvement_draft":
        draft = AIDraft.objects.create(
            user=action.user, kind=AIDraft.Kind.CV_IMPROVEMENT, title=args["title"],
            payload={
                "opportunity_id": args.get("opportunity_id"), "opportunity": args.get("opportunity_title", ""),
                "professional_headline": args["professional_headline"], "summary": args["summary"],
                "skills": args.get("skills", []), "achievement_rewrites": args.get("achievement_rewrites", []),
                "recommendations": args.get("recommendations", []),
            },
        )
        result = {"draft_id": draft.id, "kind": draft.kind, "title": draft.title, "path": "/assistant/drafts"}

    elif action.tool_name == "save_cover_letter_draft":
        draft = AIDraft.objects.create(
            user=action.user, kind=AIDraft.Kind.COVER_LETTER, title=args["title"],
            payload={
                "opportunity_id": args["opportunity_id"], "opportunity": args.get("opportunity_title", ""),
                "content": args["content"], "key_points": args.get("key_points", []),
            },
        )
        result = {"draft_id": draft.id, "kind": draft.kind, "title": draft.title, "path": "/assistant/drafts"}

    elif action.tool_name == "save_learning_gap_plan_draft":
        draft = AIDraft.objects.create(
            user=action.user, kind=AIDraft.Kind.LEARNING_GAP_PLAN, title=args["title"],
            payload={
                "opportunity_id": args["opportunity_id"], "opportunity": args.get("opportunity_title", ""),
                "missing_skills": args.get("missing_skills", []), "actions": args.get("actions", []),
            },
        )
        result = {"draft_id": draft.id, "kind": draft.kind, "title": draft.title, "path": "/assistant/drafts"}

    elif action.tool_name == "save_candidate_interview_prep_draft":
        draft = AIDraft.objects.create(
            user=action.user, kind=AIDraft.Kind.INTERVIEW_PREP, title=args["title"],
            payload={
                "opportunity_id": args["opportunity_id"], "opportunity": args.get("opportunity_title", ""),
                "pitch": args["pitch"], "likely_questions": args.get("likely_questions", []),
                "star_examples": args.get("star_examples", []), "questions_to_ask": args.get("questions_to_ask", []),
                "checklist": args.get("checklist", []),
            },
        )
        result = {"draft_id": draft.id, "kind": draft.kind, "title": draft.title, "path": "/assistant/drafts"}

    elif action.tool_name == "save_quiz_draft":
        draft = AIDraft.objects.create(user=action.user, kind=AIDraft.Kind.QUIZ, title=args["title"], course_id=args.get("course_id"), payload={"questions": args["questions"]})
        result = {"draft_id": draft.id, "kind": draft.kind, "title": draft.title, "path": "/assistant/drafts"}

    elif action.tool_name == "save_course_outline_draft":
        draft = AIDraft.objects.create(user=action.user, kind=AIDraft.Kind.COURSE_OUTLINE, title=args["title"], payload={"description": args.get("description", ""), "sections": args["sections"]})
        result = {"draft_id": draft.id, "kind": draft.kind, "title": draft.title, "path": "/assistant/drafts"}

    elif action.tool_name == "create_course_draft":
        with transaction.atomic():
            course = Course.objects.create(
                instructor=action.user,
                category_id=args.get("category_id"),
                title=args["title"],
                subtitle=args.get("subtitle", ""),
                description=args["description"],
                what_you_will_learn=args.get("what_you_will_learn", []),
                requirements=args.get("requirements", []),
                target_audience=args.get("target_audience", []),
                level=args.get("level", "beginner"),
                language=args.get("language", "Français"),
                published=False,
                certificate_number_prefix="KP-CERT",
            )
            for section_order, section_data in enumerate(args["sections"], start=1):
                section = Section.objects.create(course=course, title=section_data["title"], order=section_order)
                for lesson_order, lesson_data in enumerate(section_data["lessons"], start=1):
                    Lesson.objects.create(
                        section=section,
                        title=lesson_data["title"],
                        description=lesson_data.get("description", ""),
                        order=lesson_order,
                    )
            course.refresh_aggregates()
        result = {
            "course_id": course.id,
            "title": course.title,
            "published": False,
            "path": f"/dashboard/instructor/courses/{course.id}/edit",
            "content_path": f"/dashboard/instructor/courses/{course.id}",
        }

    elif action.tool_name == "save_mentorship_plan_draft":
        booking = MentorshipBooking.objects.select_related("offering", "user", "slot").get(pk=args["booking_id"])
        draft = AIDraft.objects.create(
            user=action.user,
            kind=AIDraft.Kind.MENTOR_PLAN,
            title=args["title"],
            payload={
                "booking_id": booking.id,
                "offering": booking.offering.title,
                "learner": booking.user.get_full_name() or booking.user.username,
                "starts_at": booking.slot.starts_at.isoformat(),
                "objectives": args.get("objectives", []),
                "agenda": args.get("agenda", []),
                "questions": args.get("questions", []),
                "follow_up": args.get("follow_up", []),
            },
        )
        result = {"draft_id": draft.id, "kind": draft.kind, "title": draft.title, "path": "/assistant/drafts"}

    elif action.tool_name == "save_interview_rubric_draft":
        application = _recruiter_application(action.user, args["application_id"])
        draft = AIDraft.objects.create(
            user=action.user,
            kind=AIDraft.Kind.INTERVIEW_RUBRIC,
            title=args["title"],
            payload={
                "application_id": application.id,
                "candidate": application.candidate_name_snapshot,
                "opportunity": application.opportunity.title,
                "criteria": args.get("criteria", []),
                "questions": args.get("questions", []),
            },
        )
        result = {"draft_id": draft.id, "kind": draft.kind, "title": draft.title, "path": "/assistant/drafts"}

    elif action.tool_name == "update_application_stage":
        with transaction.atomic():
            application = OpportunityApplication.objects.select_for_update().select_related("opportunity__employer").get(pk=args["application_id"])
            # Revalide l'appartenance et l'état au moment exact de la confirmation.
            _recruiter_application(action.user, application.id)
            if application.status in {
                OpportunityApplication.Status.WITHDRAWN,
                OpportunityApplication.Status.HIRED,
                OpportunityApplication.Status.REJECTED,
            }:
                raise ValueError("Cette candidature est dans un état final.")
            application.status = args["status"]
            if args.get("recruiter_note"):
                application.recruiter_note = args["recruiter_note"]
            application.save(update_fields=["status", "recruiter_note", "updated_at"])
        result = {
            "application_id": application.id,
            "status": application.status,
            "path": "/dashboard/employer",
        }
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
