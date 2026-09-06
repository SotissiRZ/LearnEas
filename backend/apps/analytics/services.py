import hashlib
import re
from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.enrollments.models import CourseEnrollment, PDFPurchase, Certificate
from apps.formations.models import FormationEnrollment, MentorshipBooking
from apps.opportunities.models import OpportunityApplication, RecruitmentInterview, EmploymentOffer
from apps.payments.models import Order, OrderItem
from .models import ProductEvent

User = get_user_model()

ALLOWED_PROPERTY_KEYS = {
    "kind", "result_type", "result_id", "query_length", "results_count", "source",
    "mode", "quality", "content_type", "content_id", "position_bucket", "completion_percent",
}
SAFE_VALUE = re.compile(r"^[\w .,:+/%-]{0,120}$", re.UNICODE)


SENSITIVE_PATH_PREFIXES = (
    "/reset-password", "/verify-email", "/checkout/return", "/auth/", "/admin/login",
)


def sanitize_path(value):
    path = str(value or "").split("?", 1)[0].split("#", 1)[0]
    if not path.startswith("/"):
        return ""
    if any(path.startswith(prefix) for prefix in SENSITIVE_PATH_PREFIXES):
        return ""
    return path[:240]


def sanitize_properties(raw):
    clean = {}
    if not isinstance(raw, dict):
        return clean
    for key in ALLOWED_PROPERTY_KEYS:
        if key not in raw:
            continue
        value = raw[key]
        if isinstance(value, bool) or value is None:
            clean[key] = value
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            clean[key] = value
        else:
            text = str(value)[:120]
            if SAFE_VALUE.fullmatch(text):
                clean[key] = text
    return clean


def hashed_session(value):
    raw = str(value or "").strip()[:160]
    if not raw:
        return ""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def period_window(days):
    days = min(max(int(days or 30), 7), 365)
    end = timezone.now()
    start = end - timedelta(days=days)
    previous_start = start - timedelta(days=days)
    return days, start, end, previous_start


def _money(value):
    return str((value or Decimal("0")).quantize(Decimal("0.01")))


def _pct(numerator, denominator):
    if not denominator:
        return 0.0
    return round(float(numerator) * 100.0 / float(denominator), 1)


def _count_by_day(qs, field):
    return {
        row["day"].isoformat(): row["count"]
        for row in qs.annotate(day=TruncDate(field)).values("day").annotate(count=Count("id")).order_by("day")
        if row["day"]
    }


def _sum_by_day(qs, field, amount_field):
    return {
        row["day"].isoformat(): float(row["amount"] or 0)
        for row in qs.annotate(day=TruncDate(field)).values("day").annotate(amount=Sum(amount_field)).order_by("day")
        if row["day"]
    }


def analytics_snapshot(days=30):
    days, start, end, previous_start = period_window(days)

    users = User.objects.filter(date_joined__gte=start, date_joined__lt=end)
    previous_users = User.objects.filter(date_joined__gte=previous_start, date_joined__lt=start)
    orders = Order.objects.filter(created_at__gte=start, created_at__lt=end)
    paid = Order.objects.filter(paid_at__gte=start, paid_at__lt=end).exclude(status=Order.Status.FAILED)
    refunded = Order.objects.filter(refunded_at__gte=start, refunded_at__lt=end)

    gmv = paid.aggregate(v=Sum("total_amount"))["v"] or Decimal("0")
    refunds = refunded.aggregate(v=Sum("total_amount"))["v"] or Decimal("0")
    gross_platform_fees = OrderItem.objects.filter(order__paid_at__gte=start, order__paid_at__lt=end).aggregate(v=Sum("platform_fee_amount"))["v"] or Decimal("0")
    refunded_platform_fees = OrderItem.objects.filter(order__refunded_at__gte=start, order__refunded_at__lt=end).aggregate(v=Sum("platform_fee_amount"))["v"] or Decimal("0")

    course_enrollments = CourseEnrollment.objects.filter(purchased_at__gte=start, purchased_at__lt=end)
    course_completions = CourseEnrollment.all_objects.filter(completed_at__gte=start, completed_at__lt=end, completed=True)
    formation_enrollments = FormationEnrollment.objects.filter(enrolled_at__gte=start, enrolled_at__lt=end)
    pdf_purchases = PDFPurchase.objects.filter(purchased_at__gte=start, purchased_at__lt=end)
    certificates = Certificate.objects.filter(issued_at__gte=start, issued_at__lt=end)
    mentorships = MentorshipBooking.objects.filter(created_at__gte=start, created_at__lt=end)

    applications = OpportunityApplication.objects.filter(applied_at__gte=start, applied_at__lt=end)
    interviews = RecruitmentInterview.objects.filter(created_at__gte=start, created_at__lt=end)
    offers = EmploymentOffer.objects.filter(created_at__gte=start, created_at__lt=end)
    hires = OpportunityApplication.objects.filter(status=OpportunityApplication.Status.HIRED, updated_at__gte=start, updated_at__lt=end)

    product_events = ProductEvent.objects.filter(occurred_at__gte=start, occurred_at__lt=end)
    previous_events = ProductEvent.objects.filter(occurred_at__gte=previous_start, occurred_at__lt=start, user__isnull=False)
    current_user_ids = set(product_events.filter(user__isnull=False).values_list("user_id", flat=True).distinct())
    previous_user_ids = set(previous_events.values_list("user_id", flat=True).distinct())
    returning = len(current_user_ids & previous_user_ids)

    event_counts = list(product_events.values("event_name").annotate(count=Count("id")).order_by("-count")[:12])
    top_paths = list(product_events.filter(event_name=ProductEvent.EventName.PAGE_VIEW).exclude(path="").values("path").annotate(count=Count("id")).order_by("-count")[:10])

    top_courses = list(
        CourseEnrollment.objects.filter(purchased_at__gte=start, purchased_at__lt=end)
        .values("course__title").annotate(count=Count("id")).order_by("-count")[:6]
    )
    top_formations = list(
        FormationEnrollment.objects.filter(enrolled_at__gte=start, enrolled_at__lt=end)
        .values("formation__title").annotate(count=Count("id")).order_by("-count")[:6]
    )

    registrations_by_day = _count_by_day(users, "date_joined")
    paid_by_day = _count_by_day(paid, "paid_at")
    gmv_by_day = _sum_by_day(paid, "paid_at", "total_amount")
    active_by_day = {
        row["day"].isoformat(): row["count"]
        for row in product_events.filter(user__isnull=False).annotate(day=TruncDate("occurred_at")).values("day").annotate(count=Count("user_id", distinct=True)).order_by("day")
        if row["day"]
    }
    applications_by_day = _count_by_day(applications, "applied_at")

    timeline = []
    cursor = start.date()
    while cursor <= end.date():
        key = cursor.isoformat()
        timeline.append({
            "date": key,
            "registrations": registrations_by_day.get(key, 0),
            "active_users": active_by_day.get(key, 0),
            "paid_orders": paid_by_day.get(key, 0),
            "gmv": round(gmv_by_day.get(key, 0.0), 2),
            "applications": applications_by_day.get(key, 0),
        })
        cursor += timedelta(days=1)

    checkout_count = orders.count()
    paid_count = paid.count()
    application_count = applications.count()
    interview_count = interviews.count()
    offer_count = offers.count()
    hire_count = hires.count()

    return {
        "period_days": days,
        "generated_at": end,
        "coverage": {
            "product_events_started_at": ProductEvent.objects.order_by("occurred_at").values_list("occurred_at", flat=True).first(),
            "note": "Les événements produit sont disponibles à partir de v87. Les métriques métier historiques sont dérivées directement de PostgreSQL.",
        },
        "acquisition": {
            "registrations": users.count(),
            "previous_registrations": previous_users.count(),
            "active_users": len(current_user_ids),
            "anonymous_sessions": product_events.filter(user__isnull=True).exclude(session_key="").values("session_key").distinct().count(),
            "returning_users": returning,
            "retention_rate": _pct(returning, len(previous_user_ids)),
        },
        "finance": {
            "orders_started": checkout_count,
            "paid_orders": paid_count,
            "failed_orders": orders.filter(status=Order.Status.FAILED).count(),
            "refunded_orders": refunded.count(),
            "checkout_conversion_rate": _pct(paid_count, checkout_count),
            "gmv": _money(gmv),
            "refunds": _money(refunds),
            "net_gmv": _money(gmv - refunds),
            "platform_fees": _money(gross_platform_fees),
            "net_platform_fees": _money(gross_platform_fees - refunded_platform_fees),
        },
        "learning": {
            "course_enrollments": course_enrollments.count(),
            "course_completions": course_completions.count(),
            "formation_enrollments": formation_enrollments.count(),
            "pdf_purchases": pdf_purchases.count(),
            "mentorship_bookings": mentorships.count(),
            "certificates_issued": certificates.count(),
        },
        "recruitment": {
            "applications": application_count,
            "interviews": interview_count,
            "offers": offer_count,
            "hires": hire_count,
            "application_to_interview_rate": _pct(interview_count, application_count),
            "interview_to_offer_rate": _pct(offer_count, interview_count),
            "offer_to_hire_rate": _pct(hire_count, offer_count),
        },
        "funnels": {
            "commerce": [
                {"label": "Commandes créées", "value": checkout_count},
                {"label": "Paiements confirmés", "value": paid_count},
                {"label": "Accès cours", "value": course_enrollments.count()},
            ],
            "recruitment": [
                {"label": "Candidatures", "value": application_count},
                {"label": "Entretiens", "value": interview_count},
                {"label": "Offres", "value": offer_count},
                {"label": "Embauches", "value": hire_count},
            ],
        },
        "engagement": {
            "events": event_counts,
            "top_paths": top_paths,
            "top_courses": [{"title": row["course__title"] or "", "count": row["count"]} for row in top_courses],
            "top_formations": [{"title": row["formation__title"] or "", "count": row["count"]} for row in top_formations],
        },
        "timeline": timeline,
    }
