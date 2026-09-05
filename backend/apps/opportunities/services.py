from __future__ import annotations

from decimal import Decimal
from datetime import timedelta
import json
from django.db import models, transaction
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
    # `share_portfolio=False` doit empêcher toute fuite indirecte des preuves KalanPro.
    # On conserve uniquement les compétences déclarées dans le profil candidat ; les
    # compétences issues du portfolio/certificats ne sont agrégées que si le candidat
    # a explicitement choisi de partager ces preuves avec cette candidature.
    skills = candidate_skills_for(user, profile) if share_portfolio else clean_strings(
        (profile.skills if profile else []), max_items=60, max_length=100
    )
    portfolio_data = {}
    verified_projects = []
    certificates = []
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



def _entitlement_now(now=None):
    return now or timezone.now()


def active_employer_entitlements(employer, *, now=None):
    """Droits non révoqués, payés et dont la fenêtre courante/future existe encore."""
    from .models import EmployerEntitlement
    from apps.payments.models import Order

    now = _entitlement_now(now)
    return EmployerEntitlement.objects.select_related("order").filter(
        employer=employer,
        revoked_at__isnull=True,
        order__status=Order.Status.PAID,
    ).filter(models.Q(ends_at__isnull=True) | models.Q(ends_at__gt=now))


def current_employer_plan(employer, *, now=None):
    """Retourne `business`, `pro` ou `starter` pour l'instant courant."""
    from .models import EmployerEntitlement

    now = _entitlement_now(now)
    current = active_employer_entitlements(employer, now=now).filter(
        kind__in=[EmployerEntitlement.Kind.PRO, EmployerEntitlement.Kind.BUSINESS],
        starts_at__lte=now,
        ends_at__gt=now,
    )
    if current.filter(kind=EmployerEntitlement.Kind.BUSINESS).exists():
        return EmployerEntitlement.Kind.BUSINESS
    if current.filter(kind=EmployerEntitlement.Kind.PRO).exists():
        return EmployerEntitlement.Kind.PRO
    return "starter"


def employer_active_job_limit(employer, *, now=None):
    from apps.accounts.models import PlatformSettings
    from .models import EmployerEntitlement

    config = PlatformSettings.load()
    plan = current_employer_plan(employer, now=now)
    if plan == EmployerEntitlement.Kind.BUSINESS:
        return int(config.employer_business_active_jobs)
    if plan == EmployerEntitlement.Kind.PRO:
        return int(config.employer_pro_active_jobs)
    return int(config.employer_free_active_jobs)


def employer_has_talent_pool_access(employer, *, now=None):
    from .models import EmployerEntitlement
    return current_employer_plan(employer, now=now) in {
        EmployerEntitlement.Kind.PRO,
        EmployerEntitlement.Kind.BUSINESS,
    }


def available_single_post_entitlement(employer):
    """Crédit payé, non révoqué et encore inutilisé.

    Le délai de 30 jours démarre à la consommation pour ne pas pénaliser un recruteur
    qui achète le crédit avant d'avoir finalisé son annonce.
    """
    from .models import EmployerEntitlement
    from apps.payments.models import Order

    return EmployerEntitlement.objects.select_for_update().filter(
        employer=employer,
        kind=EmployerEntitlement.Kind.SINGLE_POST,
        revoked_at__isnull=True,
        consumed_at__isnull=True,
        order__status=Order.Status.PAID,
    ).order_by("created_at", "id").first()


def claim_publication_right(employer, *, opportunity=None, requested_deadline=None, now=None):
    """Vérifie le quota et consomme un crédit à l'unité si nécessaire.

    Retourne `(entitlement, effective_deadline)`. `entitlement` vaut None quand
    la publication entre dans le quota Starter/Pro/Business.
    """
    from .models import Opportunity

    now = _entitlement_now(now)
    active_qs = Opportunity.objects.filter(
        employer=employer,
        status=Opportunity.Status.PUBLISHED,
    ).filter(models.Q(application_deadline__isnull=True) | models.Q(application_deadline__gt=now))
    if opportunity and opportunity.pk:
        active_qs = active_qs.exclude(pk=opportunity.pk)

    if active_qs.count() < employer_active_job_limit(employer, now=now):
        return None, requested_deadline

    credit = available_single_post_entitlement(employer)
    if not credit:
        raise ValueError(
            "Votre quota d'offres actives est atteint. Achetez une annonce à l'unité "
            "ou activez un plan Pro/Business."
        )

    paid_until = now + timedelta(days=30)
    if requested_deadline and requested_deadline > paid_until:
        raise ValueError("Une annonce payée à l'unité ne peut pas être publiée pendant plus de 30 jours.")

    credit.starts_at = now
    credit.ends_at = paid_until
    credit.consumed_at = now
    credit.consumed_by = opportunity
    credit.save(update_fields=["starts_at", "ends_at", "consumed_at", "consumed_by", "updated_at"])
    return credit, (requested_deadline or paid_until)


@transaction.atomic
def activate_employer_entitlement(order, *, kind):
    """Matérialise le droit associé à une commande employeur payée.

    Les renouvellements Pro/Business sont chaînés sans chevauchement : un nouvel achat
    commence à la fin de la dernière période non révoquée du même plan.
    """
    from .models import EmployerEntitlement, EmployerProfile

    employer = EmployerProfile.objects.select_for_update().filter(user=order.user).first()
    if not employer:
        raise ValueError("Profil entreprise introuvable pour cette commande.")

    entitlement, _ = EmployerEntitlement.objects.select_for_update().get_or_create(
        order=order,
        defaults={
            "employer": employer,
            "kind": kind,
            "entitlement_key": f"employer:{kind}:order:{order.pk}",
        },
    )
    if entitlement.revoked_at is not None:
        raise ValueError("Le droit associé à cette commande a été révoqué.")
    if entitlement.employer_id != employer.id or entitlement.kind != kind:
        raise ValueError("La commande est déjà rattachée à un autre droit employeur.")

    # Idempotence : un droit déjà activé ne doit jamais être allongé par un replay webhook.
    if entitlement.starts_at is not None:
        return entitlement

    now = order.paid_at or timezone.now()
    if kind == EmployerEntitlement.Kind.SINGLE_POST:
        entitlement.starts_at = now
        entitlement.ends_at = None  # la fenêtre de 30 jours démarre lors de la publication.
    else:
        latest_end = EmployerEntitlement.objects.filter(
            employer=employer,
            kind=kind,
            revoked_at__isnull=True,
            order__status="paid",
            ends_at__isnull=False,
        ).exclude(pk=entitlement.pk).aggregate(v=models.Max("ends_at"))["v"]
        start = max(now, latest_end) if latest_end else now
        entitlement.starts_at = start
        entitlement.ends_at = start + timedelta(days=30)

    entitlement.save(update_fields=["starts_at", "ends_at", "updated_at"])
    return entitlement


@transaction.atomic
def revoke_employer_entitlement(order, *, reason="Commande remboursée"):
    """Révoque le droit d'une commande et recale les renouvellements futurs."""
    from .models import EmployerEntitlement, Opportunity

    entitlement = EmployerEntitlement.objects.select_for_update().filter(order=order).first()
    if not entitlement or entitlement.revoked_at is not None:
        return False

    now = timezone.now()
    entitlement.revoked_at = now
    entitlement.revocation_reason = str(reason or "Commande remboursée")[:500]
    entitlement.save(update_fields=["revoked_at", "revocation_reason", "updated_at"])

    if entitlement.kind == EmployerEntitlement.Kind.SINGLE_POST:
        # Le remboursement rend le crédit invalide même s'il a déjà été utilisé.
        if entitlement.consumed_by_id:
            Opportunity.objects.filter(
                pk=entitlement.consumed_by_id,
                publication_entitlement=entitlement,
                status=Opportunity.Status.PUBLISHED,
            ).update(status=Opportunity.Status.CLOSED, updated_at=now)
        return True

    # Une période déjà entièrement écoulée n'a plus de temps non consommé à rendre :
    # son remboursement tardif ne doit jamais étendre les périodes suivantes.
    if entitlement.starts_at and entitlement.ends_at and entitlement.ends_at > now:
        duration = entitlement.ends_at - entitlement.starts_at
        future = list(EmployerEntitlement.objects.select_for_update().filter(
            employer=entitlement.employer,
            kind=entitlement.kind,
            revoked_at__isnull=True,
            starts_at__gte=entitlement.ends_at,
            ends_at__isnull=False,
            order__status="paid",
        ).order_by("starts_at", "id"))
        cursor = max(now, entitlement.starts_at)
        # Si une période précédente non révoquée se termine après `cursor`, elle reste prioritaire.
        previous_end = EmployerEntitlement.objects.filter(
            employer=entitlement.employer,
            kind=entitlement.kind,
            revoked_at__isnull=True,
            ends_at__lte=entitlement.ends_at,
            ends_at__gt=cursor,
            order__status="paid",
        ).exclude(pk=entitlement.pk).aggregate(v=models.Max("ends_at"))["v"]
        if previous_end:
            cursor = max(cursor, previous_end)
        for future_entitlement in future:
            period = future_entitlement.ends_at - future_entitlement.starts_at
            future_entitlement.starts_at = cursor
            future_entitlement.ends_at = cursor + (period or duration)
            future_entitlement.save(update_fields=["starts_at", "ends_at", "updated_at"])
            cursor = future_entitlement.ends_at
    return True


def record_application_event(application, *, actor=None, event_type, label, metadata=None):
    from .models import ApplicationHistoryEvent
    return ApplicationHistoryEvent.objects.create(
        application=application,
        actor=actor,
        event_type=str(event_type)[:64],
        label=str(label)[:220],
        metadata=metadata or {},
    )
