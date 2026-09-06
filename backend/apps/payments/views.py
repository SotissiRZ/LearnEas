from decimal import Decimal, ROUND_HALF_UP
import logging
import hashlib
import hmac
import json
import csv
import time
from datetime import timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import HttpResponse, HttpResponseRedirect
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from apps.accounts.models import User, PlatformSettings, InstructorApplication
from apps.catalog.models import Course, PDFProduct
from apps.enrollments.models import CourseEnrollment, PDFPurchase
from apps.formations.models import InteractiveFormation, FormationEnrollment, FormationSession, FormationAttendance, MentorshipBooking, MentorshipPack, MentorshipPass, FormationKind
from .models import (
    Order, OrderItem, PayoutProfile, InstructorPayout, FormationSeatReservation, Currency,
    PaymentGateway, InstructorLedgerEntry, PaymentAttempt, PaymentEvent, PaymentIssue,
)
import stripe
from apps.common.throttles import CheckoutRateThrottle, AdminTestRateThrottle, WebhookRateThrottle

from .serializers import (
    OrderSerializer, CheckoutSerializer, PayoutProfileSerializer, InstructorPayoutSerializer,
    CurrencySerializer, PaymentGatewaySerializer, PaymentAttemptSerializer, PaymentEventSerializer,
    PaymentIssueSerializer,
)
from .providers import (
    ProviderError, create_checkout, test_provider, verify_payment, is_configured,
    _from_minor_units, normalize_provider_amount, _cinetpay_config,
)
from .services import record_payout_ledger, record_sale_ledger, revoke_order_entitlements
from .lifecycle import (
    classify_verification, create_attempt, mark_attempt_failed, mark_attempt_paid, mark_attempt_redirected,
    open_issue, payload_hash, record_event, register_provider_error, resolve_order_issues,
)

logger = logging.getLogger(__name__)

MONEY = Decimal("0.01")


def _request_id(request) -> str:
    return str(getattr(request, "request_id", "") or "")[:100]


class IsAdminRole(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "admin")


def _platform_finance_settings():
    try:
        config = PlatformSettings.load()
        return Decimal(str(config.platform_commission_percent)), Decimal(str(config.minimum_payout_amount))
    except Exception:
        return (
            Decimal(str(getattr(settings, "PLATFORM_COMMISSION_PERCENT", 15))),
            Decimal(str(getattr(settings, "MINIMUM_PAYOUT_AMOUNT", 100))),
        )


def _split_revenue(price, commission_percent=None):
    if commission_percent is None:
        commission_percent, _ = _platform_finance_settings()
    pct = Decimal(str(commission_percent)) / Decimal("100")
    price = Decimal(price)
    fee = (price * pct).quantize(MONEY, rounding=ROUND_HALF_UP)
    return fee, (price - fee).quantize(MONEY, rounding=ROUND_HALF_UP)


def _mentor_commission_percent():
    try:
        return Decimal(str(PlatformSettings.load().mentor_commission_percent))
    except Exception:
        return _platform_finance_settings()[0]


def _release_failed_order_reservations(order):
    """Libère uniquement les réservations liées à une commande définitivement échouée.

    Une commande encore PENDING peut être confirmée de façon asynchrone par Mobile Money
    ou carte : elle ne doit donc jamais libérer un créneau de mentorat ou une place de cohorte.
    """
    formation_ids = list(FormationSeatReservation.objects.filter(order=order).values_list("formation_id", flat=True))
    FormationSeatReservation.objects.filter(order=order).delete()
    for formation_id in formation_ids:
        try:
            from apps.formations.cohorts import refresh_waitlist
            refresh_waitlist(formation_id)
        except Exception:
            logger.exception("Impossible de rafraîchir la liste d'attente de la formation %s", formation_id)
    now = timezone.now()
    MentorshipBooking.objects.filter(
        order_items__order=order,
        status=MentorshipBooking.Status.PENDING_PAYMENT,
    ).update(
        status=MentorshipBooking.Status.EXPIRED,
        expires_at=None,
        updated_at=now,
    )


def _finance_totals(instructor):
    paid_items = OrderItem.objects.filter(instructor=instructor, order__status=Order.Status.PAID)
    gross = paid_items.aggregate(v=Sum("unit_price"))["v"] or Decimal("0")
    net_earnings = InstructorLedgerEntry.objects.filter(
        instructor=instructor,
        entry_type__in=[InstructorLedgerEntry.EntryType.SALE, InstructorLedgerEntry.EntryType.REFUND],
    ).aggregate(v=Sum("amount"))["v"] or Decimal("0")
    ledger_balance = InstructorLedgerEntry.objects.filter(instructor=instructor).aggregate(v=Sum("amount"))["v"] or Decimal("0")
    pending_locked = InstructorPayout.objects.filter(
        instructor=instructor,
        status__in=[InstructorPayout.Status.PENDING, InstructorPayout.Status.PROCESSING],
    ).aggregate(v=Sum("amount"))["v"] or Decimal("0")
    paid_out = InstructorPayout.objects.filter(
        instructor=instructor, status=InstructorPayout.Status.PAID
    ).aggregate(v=Sum("amount"))["v"] or Decimal("0")
    return {
        "gross_revenue": gross,
        "total_earnings": net_earnings,
        "available_balance": max(ledger_balance - pending_locked, Decimal("0")),
        "ledger_balance": ledger_balance,
        "paid_out": paid_out,
        "sales_count": paid_items.count(),
    }


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "provider"]
    search_fields = ["invoice_number", "user__email", "user__first_name", "user__last_name"]
    ordering_fields = ["created_at", "paid_at", "total_amount"]
    ordering = ["-created_at"]

    def get_queryset(self):
        user = self.request.user
        qs = (
            Order.objects.select_related("user")
            .prefetch_related("items__instructor", "items__course", "items__pdf_product", "items__formation", "items__mentorship_booking__offering")
            .annotate(
                open_payment_issue_count=Count(
                    "payment_issues", filter=Q(payment_issues__status=PaymentIssue.Status.OPEN), distinct=True
                )
            )
        )
        if user.role == "admin":
            if str(self.request.query_params.get("has_payment_issue") or "") == "1":
                qs = qs.filter(payment_issues__status=PaymentIssue.Status.OPEN).distinct()
            return qs
        return qs.filter(user=user)

    @action(detail=True, methods=["get"], permission_classes=[IsAdminRole], url_path="payment-audit")
    def payment_audit(self, request, pk=None):
        order = self.get_object()
        attempts = order.payment_attempts.all()[:20]
        events = order.payment_events.all()[:100]
        issues = order.payment_issues.all()[:50]
        return Response({
            "order": OrderSerializer(order).data,
            "attempts": PaymentAttemptSerializer(attempts, many=True).data,
            "events": PaymentEventSerializer(events, many=True).data,
            "issues": PaymentIssueSerializer(issues, many=True).data,
        })

    @action(detail=True, methods=["post"], permission_classes=[IsAdminRole], url_path="resolve-payment-issue")
    @transaction.atomic
    def resolve_payment_issue(self, request, pk=None):
        order = self.get_object()
        issue_id = request.data.get("issue_id")
        issue = PaymentIssue.objects.select_for_update().filter(
            pk=issue_id, order=order, status=PaymentIssue.Status.OPEN
        ).first()
        if not issue:
            return Response({"detail": "Anomalie ouverte introuvable."}, status=404)
        note = str(request.data.get("note") or "Résolution administrative")[:500]
        issue.resolve(note)
        record_event(
            order=order, source=PaymentEvent.Source.ADMIN, event_type="issue.resolved",
            outcome=PaymentEvent.Outcome.ACCEPTED, request_id=_request_id(request),
            payload={"issue_id": issue.id, "issue_type": issue.issue_type}, message=note,
        )
        return Response(PaymentIssueSerializer(issue).data)

    @action(detail=False, methods=["get"], permission_classes=[IsAdminRole], url_path="export")
    def export_csv(self, request):
        qs = self.get_queryset().order_by("-created_at")
        status_filter = str(request.query_params.get("status") or "").strip()
        provider_filter = str(request.query_params.get("provider") or "").strip()
        if status_filter in Order.Status.values:
            qs = qs.filter(status=status_filter)
        if provider_filter in Order.Provider.values:
            qs = qs.filter(provider=provider_filter)
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="kalanpro-payments-{timezone.now().date().isoformat()}.csv"'
        response.write("\ufeff")
        writer = csv.writer(response)
        writer.writerow([
            "invoice_number", "customer_email", "provider", "sandbox", "status", "provider_status",
            "payment_method", "base_total_amount", "total_amount", "currency", "created_at", "paid_at",
            "refunded_at", "last_provider_check_at",
        ])
        for order in qs.iterator(chunk_size=500):
            writer.writerow([
                order.invoice_number, order.user.email, order.provider, order.provider_sandbox, order.status,
                order.provider_status, order.payment_method, order.base_total_amount, order.total_amount, order.currency,
                order.created_at.isoformat() if order.created_at else "",
                order.paid_at.isoformat() if order.paid_at else "",
                order.refunded_at.isoformat() if order.refunded_at else "",
                order.last_provider_check_at.isoformat() if order.last_provider_check_at else "",
            ])
        return response

    @action(detail=False, methods=["get"], permission_classes=[IsAdminRole], url_path="open-payment-issues")
    def open_payment_issues(self, request):
        qs = PaymentIssue.objects.filter(status=PaymentIssue.Status.OPEN).select_related("order", "order__user")
        severity = str(request.query_params.get("severity") or "").strip()
        if severity in PaymentIssue.Severity.values:
            qs = qs.filter(severity=severity)
        rows = list(qs.order_by("-created_at")[:100])
        return Response({
            "count": qs.count(),
            "results": [
                {
                    **PaymentIssueSerializer(issue).data,
                    "order_id": issue.order_id,
                    "invoice_number": issue.order.invoice_number,
                    "provider": issue.order.provider,
                    "customer_email": issue.order.user.email,
                }
                for issue in rows
            ],
        })

    @action(detail=True, methods=["post"], permission_classes=[IsAdminRole])
    @transaction.atomic
    def set_status(self, request, pk=None):
        # Verrou métier explicite : deux actions admin concurrentes ne peuvent pas
        # rembourser/confirmer la même commande deux fois.
        visible = self.get_object()
        order = Order.objects.select_for_update().get(pk=visible.pk)
        new_status = request.data.get("status")
        if new_status not in Order.Status.values:
            return Response({"status": ["Statut invalide."]}, status=400)
        allowed = {
            Order.Status.PENDING: {Order.Status.PAID, Order.Status.FAILED},
            Order.Status.PAID: {Order.Status.REFUNDED},
            Order.Status.FAILED: set(),
            Order.Status.REFUNDED: set(),
        }
        if new_status == order.status:
            return Response(self.get_serializer(order).data)
        previous_status = order.status
        if new_status not in allowed.get(order.status, set()):
            return Response({"detail": "Transition de statut invalide."}, status=409)

        if new_status == Order.Status.PAID:
            # total_amount est la vérité du montant réellement présenté au prestataire.
            # Des commandes historiques/tests peuvent avoir base_total_amount=0 tout en
            # étant payantes : elles ne doivent pas contourner cette barrière de sécurité.
            if order.total_amount > 0 and order.provider != Order.Provider.MANUAL and not settings.DEBUG:
                return Response({"detail": "Seuls le webhook/contrôle du prestataire peuvent confirmer une commande externe."}, status=403)
            try:
                CheckoutView()._fulfill(order)
                mark_attempt_paid(order)
            except ValueError as exc:
                return Response({"detail": str(exc)}, status=409)

        elif new_status == Order.Status.REFUNDED:
            refund_reason = str(request.data.get("refund_reason") or request.data.get("reason") or "Remboursement administratif").strip()[:500]
            refund_reference = str(request.data.get("refund_reference") or request.data.get("reference") or "").strip()[:255]
            if order.provider != Order.Provider.MANUAL and not refund_reference:
                return Response({
                    "refund_reference": [
                        "La référence du remboursement confirmé par le prestataire est obligatoire avant révocation des droits."
                    ]
                }, status=400)
            if not refund_reference:
                refund_reference = f"manual-refund-{order.invoice_number or order.pk}"

            order.status = Order.Status.REFUNDED
            order.refunded_at = timezone.now()
            order.refund_reference = refund_reference
            order.refund_reason = refund_reason
            order.save(update_fields=["status", "refunded_at", "refund_reference", "refund_reason"])
            revoke_order_entitlements(order, actor=request.user, reason=refund_reason)
            resolve_order_issues(order, tuple(PaymentIssue.IssueType.values), "Commande remboursée.")

        else:
            order.status = new_status
            order.save(update_fields=["status"])
            if new_status == Order.Status.FAILED:
                mark_attempt_failed(order, provider_status="ADMIN_FAILED", message="Commande marquée échouée par un administrateur.")
                _release_failed_order_reservations(order)
                resolve_order_issues(
                    order, (PaymentIssue.IssueType.STALE_PENDING, PaymentIssue.IssueType.PROVIDER_ERROR),
                    "Commande clôturée comme échouée par un administrateur.",
                )

        record_event(
            order=order, source=PaymentEvent.Source.ADMIN, event_type="order.status_changed",
            outcome=PaymentEvent.Outcome.ACCEPTED, request_id=_request_id(request),
            payload={"from": previous_status, "to": new_status},
        )
        order.refresh_from_db()
        return Response(self.get_serializer(order).data)


class CheckoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [CheckoutRateThrottle]

    @transaction.atomic
    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = request.user
        employer_product = str(data.get("employer_product") or "").strip()
        idempotency_key = str(request.headers.get("Idempotency-Key") or "").strip()
        if len(idempotency_key) > 128 or any(ord(ch) < 33 or ord(ch) > 126 for ch in idempotency_key):
            return Response({"detail": "Clé d'idempotence invalide."}, status=400)
        if employer_product and not idempotency_key:
            return Response(
                {"detail": "Une clé d'idempotence est obligatoire pour tout achat recruteur."},
                status=400,
            )
        if employer_product:
            from apps.opportunities.models import EmployerProfile
            employer_profile = EmployerProfile.objects.filter(
                user=user, status=EmployerProfile.Status.APPROVED
            ).first()
            if user.role != "employer" or not employer_profile:
                return Response(
                    {"detail": "Un espace recruteur approuvé est requis pour acheter ce produit."},
                    status=403,
                )
        request_fingerprint = hashlib.sha256(
            json.dumps(data, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        ).hexdigest()
        if idempotency_key:
            existing = Order.objects.filter(user=user, idempotency_key=idempotency_key).first()
            if existing:
                if existing.request_fingerprint and existing.request_fingerprint != request_fingerprint:
                    return Response({"detail": "Cette clé d'idempotence a déjà été utilisée pour un autre panier."}, status=409)
                return Response({
                    "order": OrderSerializer(existing).data,
                    "requires_payment": existing.base_total_amount > 0,
                    "checkout_url": existing.checkout_url or None,
                    "manual_review": bool(existing.base_total_amount > 0 and existing.provider == Order.Provider.MANUAL and existing.status == Order.Status.PENDING),
                    "test_payment": bool(existing.provider == Order.Provider.MANUAL and existing.provider_sandbox and existing.status == Order.Status.PAID),
                    "idempotent_replay": True,
                }, status=200)
        test_payment = bool(data.get("test_payment"))
        if test_payment and not settings.TEST_PAYMENTS_ENABLED:
            return Response({"detail": "Les paiements de test sont désactivés sur cet environnement."}, status=403)

        currency = Currency.objects.filter(code=data["currency"], is_active=True).first()
        if not currency:
            return Response({"currency": ["Cette devise n'est pas active."]}, status=400)
        # La validation du prestataire est volontairement différée jusqu'au calcul du total :
        # un contenu gratuit ne doit jamais dépendre de la disponibilité d'une passerelle externe.
        gateway = PaymentGateway.objects.filter(code=data["provider"]).first()

        owned_course_ids = set()
        owned_pdf_ids = set()
        owned_formation_ids = set()
        courses = []
        pdfs = []
        formations = []
        mentorship_bookings = []
        mentorship_packs = []
        if not employer_product:
            owned_course_ids = set(CourseEnrollment.objects.filter(user=user).values_list("course_id", flat=True))
            owned_pdf_ids = set(PDFPurchase.objects.filter(user=user).values_list("pdf_product_id", flat=True))
            owned_formation_ids = set(FormationEnrollment.objects.filter(user=user).values_list("formation_id", flat=True))
            courses = list(Course.objects.filter(id__in=[pk for pk in data["course_ids"] if pk not in owned_course_ids], published=True).select_related("instructor"))
            pdfs = list(PDFProduct.objects.filter(id__in=[pk for pk in data["pdf_ids"] if pk not in owned_pdf_ids], published=True).select_related("instructor"))
            formations = list(InteractiveFormation.objects.select_for_update().filter(
                id__in=[pk for pk in data["formation_ids"] if pk not in owned_formation_ids],
                published=True, kind=FormationKind.COHORT,
            ).select_related("instructor"))
            from apps.formations.mentorship import expire_stale_bookings
            expire_stale_bookings()
            mentorship_bookings = list(MentorshipBooking.objects.select_for_update().filter(
                id__in=data["mentorship_booking_ids"],
                user=user,
                status=MentorshipBooking.Status.PENDING_PAYMENT,
            ).select_related("offering", "offering__instructor", "slot"))
            mentorship_packs = list(MentorshipPack.objects.select_for_update().filter(
                id__in=data["mentorship_pack_ids"],
                published=True,
                offering__published=True,
            ).select_related("offering", "offering__instructor"))
        if not employer_product and not courses and not pdfs and not formations and not mentorship_bookings and not mentorship_packs:
            return Response({"detail": "Tous les éléments du panier sont déjà acquis, expirés ou indisponibles."}, status=400)

        now = timezone.now()
        unavailable = []
        for formation in formations:
            from apps.formations.cohorts import can_checkout_formation
            if not can_checkout_formation(user, formation):
                unavailable.append(formation.title)
        if unavailable:
            return Response({"detail": "Cohorte(s) complète(s), fermée(s) ou temporairement réservée(s) : " + ", ".join(unavailable)}, status=409)

        invalid_bookings = []
        for booking in mentorship_bookings:
            if booking.expires_at and booking.expires_at <= now:
                invalid_bookings.append(booking.id)
                continue
            if booking.slot.starts_at <= now:
                invalid_bookings.append(booking.id)
                continue
            if OrderItem.objects.filter(
                mentorship_booking=booking, order__status=Order.Status.PENDING
            ).exists():
                invalid_bookings.append(booking.id)
        if invalid_bookings:
            return Response({"detail": "Une réservation de mentorat est expirée ou possède déjà une commande en cours."}, status=409)

        if employer_product:
            pricing = PlatformSettings.load()
            employer_prices = {
                "single_post": pricing.employer_single_post_eur,
                "pro": pricing.employer_pro_monthly_eur,
                "business": pricing.employer_business_monthly_eur,
            }
            base_total = Decimal(employer_prices[employer_product])
        else:
            base_total = sum((Decimal("0") if c.is_free else (c.discount_price if c.discount_price is not None else c.price) for c in courses), Decimal("0"))
            base_total += sum((Decimal("0") if item.is_free else item.price for item in pdfs), Decimal("0"))
            base_total += sum((item.price for item in formations), Decimal("0"))
            base_total += sum((item.price_snapshot for item in mentorship_bookings), Decimal("0"))
            base_total += sum((pack.price for pack in mentorship_packs), Decimal("0"))
        quantum = Decimal("1").scaleb(-int(currency.decimal_places))
        payment_total = (base_total * Decimal(currency.exchange_rate)).quantize(quantum, rounding=ROUND_HALF_UP)

        if base_total > 0:
            if test_payment:
                # Bac à sable interne : aucune API bancaire n'est appelée. Les commandes
                # restent clairement marquées `manual` + `provider_sandbox=True`.
                provider_code = Order.Provider.MANUAL
            else:
                if not gateway or not gateway.is_active:
                    return Response({"provider": ["Ce moyen de paiement n'est pas actif."]}, status=400)
                if gateway.supported_currencies and currency.code not in gateway.supported_currencies:
                    return Response({"provider": [f"{gateway.name} ne prend pas en charge {currency.code}."]}, status=400)
                if gateway.code != Order.Provider.MANUAL and not is_configured(gateway.code, sandbox=gateway.sandbox):
                    mode = "test" if gateway.sandbox else "production"
                    return Response({"provider": [f"{gateway.name} est activé en mode {mode}, mais ses clés serveur correspondantes ne sont pas configurées."]}, status=503)
                provider_code = gateway.code
        else:
            # Aucune passerelle n'est contactée pour une acquisition gratuite.
            provider_code = Order.Provider.MANUAL

        # Certains wallets imposent des contraintes de montant. CinetPay exige notamment
        # un entier multiple de 5 ; le montant réellement facturé est donc figé ici et
        # devient la source de vérité de la commande avant tout appel externe.
        payment_total = normalize_provider_amount(provider_code, payment_total, currency.code)

        order_expiry = None
        if base_total > 0:
            expiry_hours = min(max(int(getattr(settings, "PAYMENT_ORDER_EXPIRY_HOURS", 24)), 1), 168)
            order_expiry = timezone.now() + timedelta(hours=expiry_hours)

        order_defaults = {
            "provider": provider_code,
            "provider_sandbox": bool(test_payment or (gateway.sandbox if base_total > 0 and gateway else False)),
            "base_total_amount": base_total,
            "total_amount": payment_total,
            "currency": currency.code,
            "request_fingerprint": request_fingerprint,
            "expires_at": order_expiry,
        }
        if idempotency_key:
            order, created = Order.objects.get_or_create(
                user=user, idempotency_key=idempotency_key, defaults=order_defaults
            )
            if not created:
                if order.request_fingerprint and order.request_fingerprint != request_fingerprint:
                    return Response({"detail": "Cette clé d'idempotence a déjà été utilisée pour un autre panier."}, status=409)
                return Response({
                    "order": OrderSerializer(order).data,
                    "requires_payment": order.base_total_amount > 0,
                    "checkout_url": order.checkout_url or None,
                    "manual_review": bool(order.base_total_amount > 0 and order.provider == Order.Provider.MANUAL and order.status == Order.Status.PENDING),
                    "test_payment": bool(order.provider == Order.Provider.MANUAL and order.provider_sandbox and order.status == Order.Status.PAID),
                    "idempotent_replay": True,
                }, status=200)
        else:
            order = Order.objects.create(user=user, **order_defaults)

        attempt = create_attempt(order)
        record_event(
            order=order, source=PaymentEvent.Source.CHECKOUT, event_type="checkout.created",
            outcome=PaymentEvent.Outcome.ACCEPTED, request_id=_request_id(request),
            payload={
                "provider": order.provider, "sandbox": order.provider_sandbox,
                "amount": str(order.total_amount), "currency": order.currency,
                "expires_at": order.expires_at.isoformat() if order.expires_at else None,
            },
        )
        for course in courses:
            price = Decimal("0") if course.is_free else (course.discount_price if course.discount_price is not None else course.price)
            fee, earning = _split_revenue(price)
            OrderItem.objects.create(order=order, item_type=OrderItem.ItemType.COURSE, course=course, instructor=course.instructor, unit_price=price, platform_fee_amount=fee, instructor_earning_amount=earning)
        for pdf in pdfs:
            price = Decimal("0") if pdf.is_free else pdf.price
            fee, earning = _split_revenue(price)
            OrderItem.objects.create(order=order, item_type=OrderItem.ItemType.PDF, pdf_product=pdf, instructor=pdf.instructor, unit_price=price, platform_fee_amount=fee, instructor_earning_amount=earning)
        for formation in formations:
            fee, earning = _split_revenue(formation.price)
            OrderItem.objects.create(order=order, item_type=OrderItem.ItemType.FORMATION, formation=formation, instructor=formation.instructor, unit_price=formation.price, platform_fee_amount=fee, instructor_earning_amount=earning)
        if employer_product:
            OrderItem.objects.create(
                order=order,
                item_type=OrderItem.ItemType.EMPLOYER,
                entitlement_code=employer_product,
                unit_price=base_total,
                platform_fee_amount=base_total,
                instructor_earning_amount=Decimal("0"),
            )
        mentorship_payment_expiry = timezone.now() + timedelta(hours=2)
        for booking in mentorship_bookings:
            # Une fois le checkout lancé, le créneau reste bloqué assez longtemps pour
            # couvrir les wallets Mobile Money dont la confirmation peut être différée.
            booking.expires_at = mentorship_payment_expiry
            booking.save(update_fields=["expires_at", "updated_at"])
            fee, earning = _split_revenue(booking.price_snapshot, _mentor_commission_percent())
            OrderItem.objects.create(
                order=order,
                item_type=OrderItem.ItemType.MENTORING,
                mentorship_booking=booking,
                instructor=booking.offering.instructor,
                unit_price=booking.price_snapshot,
                platform_fee_amount=fee,
                instructor_earning_amount=earning,
            )

        for pack in mentorship_packs:
            fee, earning = _split_revenue(pack.price, _mentor_commission_percent())
            OrderItem.objects.create(
                order=order,
                item_type=OrderItem.ItemType.MENTOR_PACK,
                mentorship_pack=pack,
                instructor=pack.offering.instructor,
                unit_price=pack.price,
                platform_fee_amount=fee,
                instructor_earning_amount=earning,
            )

        if base_total > 0:
            reservation_expiry = timezone.now() + timedelta(minutes=45)
            for formation in formations:
                FormationSeatReservation.objects.create(order=order, formation=formation, user=user, expires_at=reservation_expiry)

        if base_total == 0 or test_payment:
            self._fulfill(order)
            mark_attempt_paid(order)
            record_event(
                order=order, source=PaymentEvent.Source.CHECKOUT, event_type="checkout.fulfilled_internal",
                outcome=PaymentEvent.Outcome.ACCEPTED, request_id=_request_id(request),
                payload={"test_payment": test_payment, "free": base_total == 0},
            )
            checkout_url = None
        elif provider_code == Order.Provider.MANUAL:
            PaymentAttempt.objects.filter(pk=attempt.pk).update(status=PaymentAttempt.Status.PENDING)
            Order.objects.filter(pk=order.pk).update(provider_status="MANUAL_REVIEW")
            order.provider_status = "MANUAL_REVIEW"
            record_event(
                order=order, source=PaymentEvent.Source.CHECKOUT, event_type="checkout.manual_pending",
                outcome=PaymentEvent.Outcome.ACCEPTED, request_id=_request_id(request),
            )
            checkout_url = None
        else:
            try:
                checkout_url, reference = create_checkout(order, user)
            except ProviderError as exc:
                transaction.set_rollback(True)
                return Response({"provider": [str(exc)]}, status=502)
            order.provider_reference = reference
            order.provider_status = "REDIRECTED"
            order.checkout_url = checkout_url or ""
            order.save(update_fields=["provider_reference", "provider_status", "checkout_url"])
            mark_attempt_redirected(order, reference=reference)
            record_event(
                order=order, source=PaymentEvent.Source.CHECKOUT, event_type="checkout.redirect_created",
                outcome=PaymentEvent.Outcome.ACCEPTED, request_id=_request_id(request),
                payload={"reference": reference},
            )

        return Response({
            "order": OrderSerializer(order).data,
            "requires_payment": base_total > 0,
            "checkout_url": checkout_url,
            "manual_review": bool(base_total > 0 and provider_code == Order.Provider.MANUAL and not test_payment),
            "test_payment": test_payment,
        }, status=201)

    @transaction.atomic
    def _fulfill(self, order):
        # Verrouille la commande : deux webhooks/retries concurrents ne peuvent pas exécuter
        # deux fois les effets métier ni envoyer plusieurs confirmations.
        order = Order.objects.select_for_update().get(pk=order.pk)
        if order.status in {Order.Status.FAILED, Order.Status.REFUNDED}:
            raise ValueError("Cette commande ne peut plus être exécutée.")
        newly_paid = order.status != Order.Status.PAID
        if newly_paid:
            order.status = Order.Status.PAID
            order.paid_at = timezone.now()
            order.save(update_fields=["status", "paid_at"])
        elif not order.paid_at:
            order.paid_at = timezone.now()
            order.save(update_fields=["paid_at"])

        for item in order.items.select_related(
            "course", "pdf_product", "formation", "mentorship_booking__offering", "mentorship_booking__slot", "mentorship_pack__offering"
        ).all():
            if item.item_type == OrderItem.ItemType.EMPLOYER:
                from apps.opportunities.models import EmployerEntitlement
                from apps.opportunities.services import activate_employer_entitlement
                if item.entitlement_code not in EmployerEntitlement.Kind.values:
                    raise ValueError("Produit recruteur invalide sur la commande.")
                activate_employer_entitlement(order, kind=item.entitlement_code)
            if item.course:
                enrollment, created = CourseEnrollment.all_objects.get_or_create(
                    user=order.user, course=item.course, defaults={"source_order": order}
                )
                if not created and enrollment.revoked_at is not None:
                    enrollment.revoked_at = None
                    enrollment.revocation_reason = ""
                    enrollment.source_order = order
                    enrollment.certificate_issued = False
                    enrollment.save(update_fields=["revoked_at", "revocation_reason", "source_order", "certificate_issued"])
                elif not created and enrollment.source_order_id is None:
                    # Réparation d'un ancien droit créé avant le rattachement aux commandes.
                    enrollment.source_order = order
                    enrollment.save(update_fields=["source_order"])
                item.course.students_count = item.course.enrollments.count()
                item.course.save(update_fields=["students_count"])

            if item.pdf_product:
                purchase, created = PDFPurchase.all_objects.get_or_create(
                    user=order.user, pdf_product=item.pdf_product, defaults={"source_order": order}
                )
                reactivated = False
                if not created and purchase.revoked_at is not None:
                    purchase.revoked_at = None
                    purchase.revocation_reason = ""
                    purchase.source_order = order
                    purchase.save(update_fields=["revoked_at", "revocation_reason", "source_order"])
                    reactivated = True
                elif not created and purchase.source_order_id is None:
                    purchase.source_order = order
                    purchase.save(update_fields=["source_order"])
                if created or reactivated:
                    item.pdf_product.downloads_count += 1
                    item.pdf_product.save(update_fields=["downloads_count"])

            if item.formation:
                formation = InteractiveFormation.objects.select_for_update().get(pk=item.formation_id)
                enrollment = FormationEnrollment.all_objects.filter(user=order.user, formation=formation).first()
                if enrollment is None or enrollment.revoked_at is not None:
                    now = timezone.now()
                    reservation = FormationSeatReservation.objects.filter(order=order, formation=formation).first()
                    reservation_valid = bool(reservation and reservation.expires_at > now)
                    active_other = FormationSeatReservation.objects.filter(
                        formation=formation, order__status=Order.Status.PENDING, expires_at__gt=now
                    ).exclude(order=order).count()
                    if formation.enrollments.count() + active_other >= formation.max_students and not reservation_valid:
                        raise ValueError(f"Plus de place disponible pour la formation {formation.title}.")
                    if enrollment is None:
                        FormationEnrollment.all_objects.create(user=order.user, formation=formation, source_order=order)
                    else:
                        enrollment.revoked_at = None
                        enrollment.revocation_reason = ""
                        enrollment.source_order = order
                        enrollment.certificate_issued = False
                        enrollment.save(update_fields=["revoked_at", "revocation_reason", "source_order", "certificate_issued"])
                elif enrollment.source_order_id is None:
                    enrollment.source_order = order
                    enrollment.save(update_fields=["source_order"])
                from apps.formations.cohorts import mark_waitlist_joined
                mark_waitlist_joined(order.user, formation)

            if item.mentorship_pack:
                expires_at = timezone.now() + timedelta(days=max(7, min(int(item.mentorship_pack.validity_days), 730)))
                MentorshipPass.objects.get_or_create(
                    user=order.user,
                    pack=item.mentorship_pack,
                    source_order=order,
                    defaults={
                        "total_sessions": item.mentorship_pack.sessions_count,
                        "remaining_sessions": item.mentorship_pack.sessions_count,
                        "expires_at": expires_at,
                    },
                )

            if item.mentorship_booking:
                from apps.formations.mentorship import confirm_booking
                confirm_booking(item.mentorship_booking)

        # Le journal est créé après les droits mais dans la même transaction. Une panne
        # d'exécution annule donc simultanément statut, droits et écritures financières.
        record_sale_ledger(order)
        FormationSeatReservation.objects.filter(order=order).delete()
        if not order.provider_status:
            order.provider_status = "PAID"
            order.save(update_fields=["provider_status"])
        mark_attempt_paid(order)
        resolve_order_issues(
            order,
            (
                PaymentIssue.IssueType.STALE_PENDING, PaymentIssue.IssueType.PROVIDER_ERROR,
                PaymentIssue.IssueType.AMOUNT_MISMATCH, PaymentIssue.IssueType.CURRENCY_MISMATCH,
                PaymentIssue.IssueType.REFERENCE_MISMATCH,
            ),
            "Commande confirmée et droits attribués.",
        )

        if newly_paid:
            # Notification après COMMIT : jamais de rollback financier à cause d'un canal externe.
            try:
                from apps.notifications.services import queue_payment_confirmation
                transaction.on_commit(lambda order_id=order.id: queue_payment_confirmation(order_id))
            except Exception:
                logger.exception("Impossible de planifier la notification WhatsApp de la commande %s", order.id)
        return order


class ConfirmPaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [CheckoutRateThrottle]

    @transaction.atomic
    def post(self, request, order_id):
        request_id = _request_id(request)
        order = Order.objects.select_for_update().filter(id=order_id, user=request.user).first()
        if not order:
            return Response({"detail": "Commande introuvable."}, status=404)
        if order.status == Order.Status.PAID:
            # Une commande payée peut avoir subi une panne entre le paiement et la
            # création des droits. Rejouer _fulfill est volontairement idempotent.
            try:
                CheckoutView()._fulfill(order)
            except ValueError as exc:
                return Response({"detail": str(exc)}, status=409)
            record_event(
                order=order, source=PaymentEvent.Source.CONFIRM, event_type="confirm.paid_replay",
                outcome=PaymentEvent.Outcome.ACCEPTED, request_id=request_id,
            )
            order.refresh_from_db()
            return Response(OrderSerializer(order).data)
        if order.status == Order.Status.REFUNDED:
            record_event(
                order=order, source=PaymentEvent.Source.CONFIRM, event_type="confirm.refunded",
                outcome=PaymentEvent.Outcome.IGNORED, request_id=request_id,
            )
            return Response({"detail": "Cette commande a été remboursée et ses droits ont été révoqués."}, status=409)
        if order.status == Order.Status.FAILED:
            record_event(
                order=order, source=PaymentEvent.Source.CONFIRM, event_type="confirm.failed",
                outcome=PaymentEvent.Outcome.IGNORED, request_id=request_id,
            )
            return Response({"detail": "Cette commande a déjà échoué. Relancez un nouveau paiement."}, status=402)
        if order.base_total_amount == 0:
            CheckoutView()._fulfill(order)
            record_event(
                order=order, source=PaymentEvent.Source.CONFIRM, event_type="confirm.free",
                outcome=PaymentEvent.Outcome.ACCEPTED, request_id=request_id,
            )
        elif order.provider == Order.Provider.MANUAL:
            record_event(
                order=order, source=PaymentEvent.Source.CONFIRM, event_type="confirm.manual_pending",
                outcome=PaymentEvent.Outcome.IGNORED, request_id=request_id,
            )
            return Response({"detail": "Le paiement manuel doit être validé par un administrateur."}, status=409)
        elif settings.DEBUG and request.data.get("dev_force") is True:
            CheckoutView()._fulfill(order)
            record_event(
                order=order, source=PaymentEvent.Source.CONFIRM, event_type="confirm.dev_force",
                outcome=PaymentEvent.Outcome.ACCEPTED, request_id=request_id,
            )
        else:
            try:
                verification = verify_payment(order)
            except ProviderError as exc:
                register_provider_error(order, str(exc), source=PaymentEvent.Source.CONFIRM, request_id=request_id)
                return Response({"detail": str(exc)}, status=502)

            classification = classify_verification(order, verification)
            record_event(
                order=order, source=PaymentEvent.Source.CONFIRM, event_type="confirm.provider_checked",
                outcome=PaymentEvent.Outcome.ACCEPTED if classification in {"paid", "pending"} else PaymentEvent.Outcome.REJECTED,
                request_id=request_id,
                payload={
                    "status": verification.get("status"), "paid": bool(verification.get("paid")),
                    "amount": verification.get("amount"), "currency": verification.get("currency"),
                    "payment_method": verification.get("payment_method"), "classification": classification,
                },
            )
            if classification in {"amount_mismatch", "currency_mismatch"}:
                return Response({"detail": "Le montant ou la devise confirmée par le prestataire ne correspond pas à la commande."}, status=409)
            if classification == "pending":
                provider_status = str(verification.get("status") or "").upper()
                terminal_failures = {"CANCELLED", "CANCELED", "FAILED"}
                # CinetPay peut faire transiter certains wallets par REFUSED avant un autre
                # état opérateur ; on ne libère donc jamais le créneau sur ce seul statut.
                if provider_status == "REFUSED" and order.provider != Order.Provider.CINETPAY:
                    terminal_failures.add("REFUSED")
                if provider_status in terminal_failures:
                    order.status = Order.Status.FAILED
                    order.save(update_fields=["status"])
                    mark_attempt_failed(order, provider_status=provider_status, message="Paiement refusé ou annulé par le prestataire.")
                    _release_failed_order_reservations(order)
                    record_event(
                        order=order, source=PaymentEvent.Source.CONFIRM, event_type="confirm.provider_failed",
                        outcome=PaymentEvent.Outcome.ACCEPTED, request_id=request_id,
                        payload={"provider_status": provider_status},
                    )
                    return Response({"detail": "Le paiement a été refusé ou annulé par le prestataire."}, status=402)
                return Response({"detail": "Le paiement est encore en attente de confirmation par le prestataire."}, status=409)

            CheckoutView()._fulfill(order)
            record_event(
                order=order, source=PaymentEvent.Source.CONFIRM, event_type="confirm.paid",
                outcome=PaymentEvent.Outcome.ACCEPTED, request_id=request_id,
                payload={"payment_method": verification.get("payment_method"), "provider_status": verification.get("status")},
            )
        order.refresh_from_db()
        return Response(OrderSerializer(order).data)


class PayoutProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _check(self, request):
        if request.user.role not in ("instructor", "admin"):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Compte instructeur requis.")

    def get(self, request):
        self._check(request)
        profile, _ = PayoutProfile.objects.get_or_create(instructor=request.user)
        return Response(PayoutProfileSerializer(profile).data)

    def patch(self, request):
        self._check(request)
        profile, _ = PayoutProfile.objects.get_or_create(instructor=request.user)
        serializer = PayoutProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class InstructorFinanceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role not in ("instructor", "admin"):
            return Response({"detail": "Compte instructeur requis."}, status=403)
        totals = _finance_totals(request.user)
        recent = OrderItem.objects.filter(
            instructor=request.user, order__status=Order.Status.PAID
        ).select_related("order", "course", "pdf_product", "formation", "mentorship_booking__offering", "mentorship_pack__offering").order_by("-order__paid_at")[:10]
        profile = PayoutProfile.objects.filter(instructor=request.user).first()
        paid_items = OrderItem.objects.filter(instructor=request.user, order__status=Order.Status.PAID)
        monthly = (
            paid_items.exclude(order__paid_at__isnull=True)
            .annotate(month=TruncMonth("order__paid_at"))
            .values("month")
            .annotate(gross=Sum("unit_price"), earning=Sum("instructor_earning_amount"), sales=Count("id"))
            .order_by("month")
        )
        top_rows = []
        for item_type in (OrderItem.ItemType.COURSE, OrderItem.ItemType.PDF, OrderItem.ItemType.FORMATION, OrderItem.ItemType.MENTORING, OrderItem.ItemType.MENTOR_PACK):
            field = {
                OrderItem.ItemType.COURSE: "course__title",
                OrderItem.ItemType.PDF: "pdf_product__title",
                OrderItem.ItemType.FORMATION: "formation__title",
                OrderItem.ItemType.MENTORING: "mentorship_booking__offering__title",
                OrderItem.ItemType.MENTOR_PACK: "mentorship_pack__offering__title",
            }[item_type]
            id_field = {
                OrderItem.ItemType.COURSE: "course_id",
                OrderItem.ItemType.PDF: "pdf_product_id",
                OrderItem.ItemType.FORMATION: "formation_id",
                OrderItem.ItemType.MENTORING: "mentorship_booking__offering_id",
                OrderItem.ItemType.MENTOR_PACK: "mentorship_pack__offering_id",
            }[item_type]
            rows = (paid_items.filter(item_type=item_type)
                .values(id_field, field)
                .annotate(sales=Count("id"), gross=Sum("unit_price"), earning=Sum("instructor_earning_amount")))
            for row in rows:
                top_rows.append({
                    "id": row[id_field], "type": item_type, "title": row[field] or "",
                    "sales": row["sales"], "gross": str(row["gross"] or 0),
                    "earning": str(row["earning"] or 0),
                })
        top_rows.sort(key=lambda r: (r["sales"], Decimal(r["gross"])), reverse=True)
        return Response({
            **{k: str(v) if isinstance(v, Decimal) else v for k, v in totals.items()},
            "commission_percent": float(_platform_finance_settings()[0]),
            "minimum_payout": str(_platform_finance_settings()[1]),
            "payout_profile_configured": bool(profile and profile.account_reference),
            "recent_sales": [
                {
                    "id": item.id,
                    "title": item.course.title if item.course else item.pdf_product.title if item.pdf_product else item.formation.title if item.formation else item.mentorship_booking.offering.title if item.mentorship_booking else item.mentorship_pack.offering.title if item.mentorship_pack else "",
                    "type": item.item_type,
                    "gross": str(item.unit_price),
                    "earning": str(item.instructor_earning_amount),
                    "paid_at": item.order.paid_at,
                }
                for item in recent
            ],
            "monthly_revenue": [
                {
                    "month": row["month"],
                    "gross": str(row["gross"] or 0),
                    "earning": str(row["earning"] or 0),
                    "sales": row["sales"],
                }
                for row in monthly
            ],
            "top_content": top_rows[:10],
        })


class InstructorPayoutViewSet(viewsets.ModelViewSet):
    serializer_class = InstructorPayoutSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "method", "instructor"]
    search_fields = ["instructor__email", "instructor__first_name", "instructor__last_name", "reference"]
    ordering_fields = ["requested_at", "processed_at", "amount"]
    ordering = ["-requested_at"]

    def get_queryset(self):
        qs = InstructorPayout.objects.select_related("instructor")
        return qs if self.request.user.role == "admin" else qs.filter(instructor=self.request.user)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        if request.user.role not in ("instructor", "admin"):
            return Response({"detail": "Compte instructeur requis."}, status=403)
        # Sérialise les demandes concurrentes d'un même instructeur pour empêcher
        # deux retraits simultanés de dépasser le solde disponible.
        User.objects.select_for_update().get(pk=request.user.pk)
        profile = PayoutProfile.objects.filter(instructor=request.user).first()
        if not profile or not profile.account_reference:
            return Response({"detail": "Configurez d'abord votre méthode de versement."}, status=400)
        try:
            amount = Decimal(str(request.data.get("amount", "0"))).quantize(MONEY)
            if not amount.is_finite() or amount <= 0:
                raise ValueError("invalid amount")
        except Exception:
            return Response({"amount": ["Montant invalide."]}, status=400)
        minimum = _platform_finance_settings()[1]
        available = _finance_totals(request.user)["available_balance"]
        if amount < minimum:
            return Response({"amount": [f"Le retrait minimum est de {minimum} EUR."]}, status=400)
        if amount > available:
            return Response({"amount": ["Le montant dépasse votre solde disponible."]}, status=400)
        payout = InstructorPayout.objects.create(
            instructor=request.user, amount=amount, method=profile.method,
            account_reference_snapshot=profile.account_reference,
        )
        return Response(InstructorPayoutSerializer(payout).data, status=201)

    @action(detail=True, methods=["post"], permission_classes=[IsAdminRole])
    @transaction.atomic
    def mark_paid(self, request, pk=None):
        visible = self.get_object()
        payout = InstructorPayout.objects.select_for_update().get(pk=visible.pk)
        reference = (request.data.get("reference") or "").strip()
        if not reference:
            return Response({"reference": ["La référence de transaction est obligatoire."]}, status=400)
        if payout.status not in (InstructorPayout.Status.PENDING, InstructorPayout.Status.PROCESSING):
            return Response({"detail": "Transition de statut invalide."}, status=409)
        payout.status = InstructorPayout.Status.PAID
        payout.processed_at = timezone.now()
        payout.reference = reference
        payout.note = request.data.get("note", "")
        payout.save(update_fields=["status", "processed_at", "reference", "note"])
        record_payout_ledger(payout)
        return Response(self.get_serializer(payout).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAdminRole])
    def mark_failed(self, request, pk=None):
        payout = self.get_object()
        if payout.status not in (InstructorPayout.Status.PENDING, InstructorPayout.Status.PROCESSING):
            return Response({"detail": "Transition de statut invalide."}, status=409)
        payout.status = InstructorPayout.Status.FAILED
        payout.processed_at = timezone.now()
        payout.note = request.data.get("note", "")
        payout.save(update_fields=["status", "processed_at", "note"])
        return Response(self.get_serializer(payout).data)


class AdminOverviewView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        paid_orders = Order.objects.filter(status=Order.Status.PAID)
        total_revenue = OrderItem.objects.filter(order__status=Order.Status.PAID).aggregate(v=Sum("unit_price"))["v"] or Decimal("0")
        platform_fees = OrderItem.objects.filter(order__status=Order.Status.PAID).aggregate(v=Sum("platform_fee_amount"))["v"] or Decimal("0")
        instructor_earnings = OrderItem.objects.filter(order__status=Order.Status.PAID).aggregate(v=Sum("instructor_earning_amount"))["v"] or Decimal("0")
        pending_payouts = InstructorPayout.objects.filter(status=InstructorPayout.Status.PENDING)
        sessions = FormationSession.objects.select_related("formation", "formation__instructor").order_by("-scheduled_at")[:12]
        platform_config = PlatformSettings.load()
        return Response({
            "users": User.objects.count(),
            "active_users": User.objects.filter(is_active=True).count(),
            "inactive_users": User.objects.filter(is_active=False).count(),
            "students": User.objects.filter(role=User.Role.STUDENT).count(),
            "employers": User.objects.filter(role=User.Role.EMPLOYER).count(),
            "instructors": User.objects.filter(role=User.Role.INSTRUCTOR).count(),
            "pending_instructor_applications": InstructorApplication.objects.filter(status=InstructorApplication.Status.PENDING).count(),
            "courses": Course.objects.count(),
            "pdfs": PDFProduct.objects.count(),
            "formations": InteractiveFormation.objects.count(),
            "orders": Order.objects.count(),
            "paid_orders": paid_orders.count(),
            "pending_orders": Order.objects.filter(status=Order.Status.PENDING).count(),
            "failed_orders": Order.objects.filter(status=Order.Status.FAILED).count(),
            "refunded_orders": Order.objects.filter(status=Order.Status.REFUNDED).count(),
            "open_payment_issues": PaymentIssue.objects.filter(status=PaymentIssue.Status.OPEN).count(),
            "critical_payment_issues": PaymentIssue.objects.filter(status=PaymentIssue.Status.OPEN, severity=PaymentIssue.Severity.CRITICAL).count(),
            "stale_payment_issues": PaymentIssue.objects.filter(status=PaymentIssue.Status.OPEN, issue_type=PaymentIssue.IssueType.STALE_PENDING).count(),
            "total_revenue": str(total_revenue),
            "platform_fees": str(platform_fees),
            "instructor_earnings": str(instructor_earnings),
            "pending_payout_count": pending_payouts.count(),
            "pending_payout_amount": str(pending_payouts.aggregate(v=Sum("amount"))["v"] or Decimal("0")),
            "platform_commission_percent": platform_config.platform_commission_percent,
            "minimum_payout_amount": str(platform_config.minimum_payout_amount),
            "recent_sessions": [
                {
                    "id": s.id,
                    "formation": s.formation.title,
                    "organizer": s.formation.instructor.get_full_name() or s.formation.instructor.username,
                    "scheduled_at": s.scheduled_at,
                    "started_at": s.started_at,
                    "ended_at": s.ended_at,
                    "actual_duration_minutes": s.actual_duration_minutes,
                    "participants": FormationAttendance.objects.filter(
                        session=s, role=FormationAttendance.Role.PARTICIPANT
                    ).values("user_id").distinct().count(),
                    "completed": s.completed,
                }
                for s in sessions
            ],
        })


class CurrencyViewSet(viewsets.ModelViewSet):
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer
    permission_classes = [IsAdminRole]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.code == "EUR":
            return Response({"detail": "EUR est la devise comptable de base et ne peut pas être supprimée."}, status=409)
        if obj.is_default:
            return Response({"detail": "La devise par défaut ne peut pas être supprimée."}, status=409)
        if Order.objects.filter(currency=obj.code).exists():
            return Response({"detail": "Cette devise est déjà utilisée par des commandes. Désactivez-la au lieu de la supprimer."}, status=409)
        if any(obj.code in (gateway.supported_currencies or []) for gateway in PaymentGateway.objects.only("supported_currencies")):
            return Response({"detail": "Cette devise est encore référencée par un moyen de paiement. Retirez-la d'abord de ses devises compatibles."}, status=409)
        return super().destroy(request, *args, **kwargs)


class PaymentGatewayViewSet(viewsets.ModelViewSet):
    queryset = PaymentGateway.objects.all()
    serializer_class = PaymentGatewaySerializer
    permission_classes = [IsAdminRole]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        if Order.objects.filter(provider=obj.code).exists():
            return Response({"detail": "Ce moyen de paiement est déjà utilisé par des commandes. Désactivez-le au lieu de le supprimer."}, status=409)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"], throttle_classes=[AdminTestRateThrottle])
    def test(self, request, pk=None):
        gateway = self.get_object()
        try:
            return Response(test_provider(gateway.code, sandbox=gateway.sandbox))
        except ProviderError as exc:
            return Response({"ok": False, "detail": str(exc)}, status=400)


class PublicPaymentConfigView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        currencies = Currency.objects.filter(is_active=True)
        gateways = PaymentGateway.objects.filter(is_active=True)
        return Response({
            "currencies": CurrencySerializer(currencies, many=True).data,
            "gateways": PaymentGatewaySerializer(gateways, many=True).data,
            "default_currency": next((item.code for item in currencies if item.is_default), "EUR"),
            "test_payments_enabled": bool(settings.TEST_PAYMENTS_ENABLED),
        })


class AdminEmailTestView(APIView):
    permission_classes = [IsAdminRole]
    throttle_classes = [AdminTestRateThrottle]

    def post(self, request):
        recipient = (request.data.get("email") or request.user.email or "").strip()
        try:
            validate_email(recipient)
        except DjangoValidationError:
            return Response({"email": ["Adresse email invalide."]}, status=400)
        try:
            from apps.notifications.email_services import create_admin_email_test_delivery, resend_runtime_status
            runtime = resend_runtime_status()
            if runtime.get("ready"):
                delivery = create_admin_email_test_delivery(user=request.user, recipient=recipient)
                return Response({
                    "ok": bool(delivery),
                    "detail": f"Email de test Resend mis en file pour {recipient}.",
                    "delivery_id": getattr(delivery, "id", None),
                    "dry_run": runtime.get("dry_run", False),
                }, status=202 if delivery else 400)
        except Exception:
            logger.exception("Échec du diagnostic Resend KalanPro")
        try:
            sent = send_mail(
                subject="Test email KalanPro",
                message="Votre configuration email KalanPro fonctionne correctement.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
        except Exception:
            logger.exception("Échec du diagnostic email KalanPro")
            return Response({"ok": False, "detail": "Échec du test email. Consultez les journaux serveur pour le détail technique."}, status=400)
        return Response({"ok": bool(sent), "detail": f"Email de test envoyé à {recipient} via le backend email de secours."})


class CinetPayReturnView(APIView):
    """Point de retour navigateur CinetPay.

    Aucune commande n'est délivrée ici : la page redirige seulement vers le frontend,
    conformément à la recommandation CinetPay. Le frontend interroge ensuite l'endpoint
    authentifié de confirmation, tandis que le webhook reste la source de vérité serveur.
    """
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def _redirect(self, request):
        transaction_id = str(
            request.data.get("transaction_id")
            or request.data.get("cpm_trans_id")
            or request.query_params.get("transaction_id")
            or request.query_params.get("cpm_trans_id")
            or ""
        ).strip()
        order_id = str(request.query_params.get("order") or "").strip()
        if not order_id and transaction_id:
            order_id = str(
                Order.objects.filter(provider=Order.Provider.CINETPAY, provider_reference=transaction_id)
                .values_list("id", flat=True).first() or ""
            )
        frontend = str(settings.FRONTEND_URL).rstrip("/")
        target = f"{frontend}/checkout/return"
        if order_id:
            target += f"?order={order_id}&provider=cinetpay"
        return HttpResponseRedirect(target)

    def get(self, request):
        return self._redirect(request)

    def post(self, request):
        return self._redirect(request)


class CinetPayWebhookView(APIView):
    """Notification serveur CinetPay authentifiée et persistamment idempotente."""
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [WebhookRateThrottle]

    _hmac_fields = (
        "cpm_site_id", "cpm_trans_id", "cpm_trans_date", "cpm_amount", "cpm_currency",
        "signature", "payment_method", "cel_phone_num", "cpm_phone_prefixe", "cpm_language",
        "cpm_version", "cpm_payment_config", "cpm_page_action", "cpm_custom",
        "cpm_designation", "cpm_error_message",
    )

    def get(self, request):
        return Response({"received": True})

    def _valid_hmac(self, request, secret_key: str) -> bool:
        received = request.META.get("HTTP_X_TOKEN", "")
        if not received or not secret_key:
            return False
        data = "".join(str(request.data.get(field) or "") for field in self._hmac_fields)
        expected = hmac.new(secret_key.encode("utf-8"), data.encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected.lower(), str(received).lower())

    def post(self, request):
        request_id = _request_id(request)
        transaction_id = str(request.data.get("cpm_trans_id") or "").strip()
        site_id = str(request.data.get("cpm_site_id") or "").strip()
        if not transaction_id or not site_id:
            return Response({"detail": "Notification CinetPay incomplète."}, status=400)

        environment = None
        configured_any = False
        for sandbox in (True, False):
            _api_key, expected_site, secret_key, _base = _cinetpay_config(sandbox)
            if expected_site and secret_key:
                configured_any = True
            if expected_site == site_id and self._valid_hmac(request, secret_key):
                environment = sandbox
                break
        if environment is None:
            if not configured_any:
                return Response({"detail": "Webhook CinetPay non configuré."}, status=503)
            return Response({"detail": "Signature CinetPay invalide."}, status=400)

        order = Order.objects.filter(
            provider=Order.Provider.CINETPAY,
            provider_reference=transaction_id,
            provider_sandbox=environment,
        ).first()
        external_id = f"{transaction_id}:{payload_hash(request.data)[:32]}"
        _event, created = record_event(
            order=order, provider=Order.Provider.CINETPAY, provider_sandbox=environment,
            source=PaymentEvent.Source.WEBHOOK, event_type="cinetpay.notification",
            external_id=external_id, outcome=PaymentEvent.Outcome.RECEIVED,
            payload=request.data, request_id=request_id,
        )
        if not created:
            return Response({"received": True, "duplicate": True})
        if not order:
            record_event(
                order=None, provider=Order.Provider.CINETPAY, provider_sandbox=environment,
                source=PaymentEvent.Source.WEBHOOK, event_type="cinetpay.unmatched",
                outcome=PaymentEvent.Outcome.IGNORED, request_id=request_id,
                payload={"transaction_id_hash": hashlib.sha256(transaction_id.encode()).hexdigest()},
            )
            return Response({"received": True, "matched": False})
        if order.status == Order.Status.PAID:
            record_event(
                order=order, source=PaymentEvent.Source.WEBHOOK, event_type="cinetpay.already_paid",
                outcome=PaymentEvent.Outcome.IGNORED, request_id=request_id,
            )
            return Response({"received": True, "paid": True, "duplicate": True})

        try:
            verification = verify_payment(order)
        except ProviderError as exc:
            register_provider_error(order, str(exc), source=PaymentEvent.Source.WEBHOOK, request_id=request_id)
            logger.exception("Échec de vérification CinetPay pour la commande %s", order.id)
            return Response({"detail": "Vérification CinetPay temporairement indisponible."}, status=502)

        classification = classify_verification(order, verification)
        if classification == "paid":
            with transaction.atomic():
                locked = Order.objects.select_for_update().get(pk=order.pk)
                if locked.status != Order.Status.PAID:
                    CheckoutView()._fulfill(locked)
            record_event(
                order=order, source=PaymentEvent.Source.WEBHOOK, event_type="cinetpay.paid",
                outcome=PaymentEvent.Outcome.ACCEPTED, request_id=request_id,
                payload={"status": verification.get("status"), "payment_method": verification.get("payment_method")},
            )
            return Response({"received": True, "paid": True})
        if classification in {"amount_mismatch", "currency_mismatch"}:
            logger.warning("CinetPay mismatch order=%s classification=%s", order.id, classification)
            record_event(
                order=order, source=PaymentEvent.Source.WEBHOOK, event_type="cinetpay.financial_mismatch",
                outcome=PaymentEvent.Outcome.REJECTED, request_id=request_id,
                payload={"classification": classification, "status": verification.get("status")},
            )
            return Response({"detail": "Montant ou devise CinetPay incohérent."}, status=409)

        record_event(
            order=order, source=PaymentEvent.Source.WEBHOOK, event_type="cinetpay.pending",
            outcome=PaymentEvent.Outcome.ACCEPTED, request_id=request_id,
            payload={"status": verification.get("status"), "payment_method": verification.get("payment_method")},
        )
        return Response({"received": True, "paid": False, "status": verification.get("status", "")})


class GeniusPayWebhookView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [WebhookRateThrottle]

    def post(self, request):
        request_id = _request_id(request)
        signature = request.META.get("HTTP_X_WEBHOOK_SIGNATURE", "")
        timestamp = request.META.get("HTTP_X_WEBHOOK_TIMESTAMP", "")
        event_name = request.META.get("HTTP_X_WEBHOOK_EVENT", "")
        if not signature or not timestamp:
            return Response({"detail": "Webhook GeniusPay incomplet."}, status=400)
        try:
            ts = int(timestamp)
        except ValueError:
            return Response({"detail": "Timestamp invalide."}, status=400)
        if abs(int(time.time()) - ts) > 300:
            return Response({"detail": "Webhook expiré."}, status=400)

        signed = timestamp.encode() + b"." + request.body
        candidates = [
            (False, getattr(settings, "GENIUSPAY_WEBHOOK_SECRET", "")),
            (True, getattr(settings, "GENIUSPAY_SANDBOX_WEBHOOK_SECRET", "")),
        ]
        sandbox_event = None
        for sandbox, secret in candidates:
            if not secret:
                continue
            expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
            if hmac.compare_digest(expected, signature):
                sandbox_event = sandbox
                break
        if sandbox_event is None:
            if not any(secret for _, secret in candidates):
                return Response({"detail": "Webhook GeniusPay non configuré."}, status=503)
            return Response({"detail": "Signature webhook invalide."}, status=400)
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except Exception:
            return Response({"detail": "JSON invalide."}, status=400)

        payload_environment = str(payload.get("environment") or "").strip().lower()
        expected_environment = "sandbox" if sandbox_event else "live"
        if payload_environment and payload_environment != expected_environment:
            return Response({"detail": "Environnement webhook GeniusPay incohérent."}, status=400)

        data = payload.get("data") or {}
        metadata = data.get("metadata") or {}
        order_id = metadata.get("order_id")
        order = Order.objects.filter(
            pk=order_id, provider=Order.Provider.GENIUSPAY, provider_sandbox=bool(sandbox_event)
        ).first() if order_id else None
        external_id = str(payload.get("id") or payload.get("event_id") or payload_hash(payload))[:191]
        _event, created = record_event(
            order=order, provider=Order.Provider.GENIUSPAY, provider_sandbox=bool(sandbox_event),
            source=PaymentEvent.Source.WEBHOOK, event_type=str(event_name or payload.get("event") or "geniuspay.notification")[:100],
            external_id=external_id, outcome=PaymentEvent.Outcome.RECEIVED,
            payload=payload, request_id=request_id,
        )
        if not created:
            return Response({"received": True, "duplicate": True})

        is_success = event_name == "payment.success" or payload.get("event") == "payment.success"
        if not is_success:
            record_event(
                order=order, provider=Order.Provider.GENIUSPAY, provider_sandbox=bool(sandbox_event),
                source=PaymentEvent.Source.WEBHOOK, event_type="geniuspay.ignored_event",
                outcome=PaymentEvent.Outcome.IGNORED, request_id=request_id,
                payload={"event": event_name or payload.get("event")},
            )
            return Response({"received": True})
        if not order:
            record_event(
                order=None, provider=Order.Provider.GENIUSPAY, provider_sandbox=bool(sandbox_event),
                source=PaymentEvent.Source.WEBHOOK, event_type="geniuspay.unmatched",
                outcome=PaymentEvent.Outcome.IGNORED, request_id=request_id,
            )
            return Response({"received": True, "matched": False})

        reference = str(data.get("reference") or data.get("id") or "")
        user_ok = str(metadata.get("user_id") or "") == str(order.user_id)
        reference_ok = bool(order.provider_reference) and reference == str(order.provider_reference)
        if not user_ok or not reference_ok:
            open_issue(
                order, PaymentIssue.IssueType.REFERENCE_MISMATCH,
                severity=PaymentIssue.Severity.CRITICAL,
                message="Le webhook GeniusPay ne correspond pas à la référence/utilisateur de la commande.",
                expected={"reference": order.provider_reference, "user_id": order.user_id},
                observed={"reference": reference, "user_id": metadata.get("user_id")},
            )
            record_event(
                order=order, source=PaymentEvent.Source.WEBHOOK, event_type="geniuspay.reference_mismatch",
                outcome=PaymentEvent.Outcome.REJECTED, request_id=request_id,
            )
            return Response({"received": True, "matched": False})

        verification = {
            "paid": True,
            "amount": Decimal(str(data.get("amount", "0"))),
            "currency": str(data.get("currency") or "").upper(),
            "status": str(data.get("status") or "SUCCESS").upper(),
            "payment_method": str(data.get("payment_method") or data.get("method") or ""),
        }
        classification = classify_verification(order, verification)
        if classification == "paid":
            with transaction.atomic():
                locked = Order.objects.select_for_update().get(pk=order.pk)
                CheckoutView()._fulfill(locked)
            resolve_order_issues(order, (PaymentIssue.IssueType.REFERENCE_MISMATCH,), "Webhook GeniusPay cohérent.")
            record_event(
                order=order, source=PaymentEvent.Source.WEBHOOK, event_type="geniuspay.paid",
                outcome=PaymentEvent.Outcome.ACCEPTED, request_id=request_id,
                payload={"status": verification["status"], "payment_method": verification["payment_method"]},
            )
        else:
            record_event(
                order=order, source=PaymentEvent.Source.WEBHOOK, event_type="geniuspay.financial_mismatch",
                outcome=PaymentEvent.Outcome.REJECTED, request_id=request_id,
                payload={"classification": classification},
            )
        return Response({"received": True})


class StripeWebhookView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [WebhookRateThrottle]

    def post(self, request):
        request_id = _request_id(request)
        signature = request.META.get("HTTP_STRIPE_SIGNATURE", "")
        candidates = [
            (False, getattr(settings, "STRIPE_WEBHOOK_SECRET", "")),
            (True, getattr(settings, "STRIPE_TEST_WEBHOOK_SECRET", "")),
        ]
        event = None
        webhook_sandbox = None
        for sandbox, secret in candidates:
            if not secret:
                continue
            try:
                event = stripe.Webhook.construct_event(request.body, signature, secret)
                webhook_sandbox = sandbox
                break
            except Exception:
                continue
        if event is None:
            if not any(secret for _, secret in candidates):
                return Response({"detail": "Webhook Stripe non configuré."}, status=503)
            return Response({"detail": "Signature webhook invalide."}, status=400)

        event_type = str(event.get("type") or "stripe.event")
        obj = (event.get("data") or {}).get("object") or {}
        order_id = (obj.get("metadata") or {}).get("order_id") or obj.get("client_reference_id")
        order = Order.objects.filter(
            pk=order_id, provider=Order.Provider.STRIPE, provider_sandbox=bool(webhook_sandbox)
        ).first() if order_id else None
        external_id = str(event.get("id") or payload_hash({"type": event_type, "object": obj}))[:191]
        _event, created = record_event(
            order=order, provider=Order.Provider.STRIPE, provider_sandbox=bool(webhook_sandbox),
            source=PaymentEvent.Source.WEBHOOK, event_type=event_type, external_id=external_id,
            outcome=PaymentEvent.Outcome.RECEIVED, request_id=request_id,
            payload={
                "type": event_type, "object_id": obj.get("id"), "payment_status": obj.get("payment_status"),
                "amount_total": obj.get("amount_total"), "currency": obj.get("currency"),
                "metadata": obj.get("metadata") or {},
            },
        )
        if not created:
            return Response({"received": True, "duplicate": True})
        if not order:
            record_event(
                order=None, provider=Order.Provider.STRIPE, provider_sandbox=bool(webhook_sandbox),
                source=PaymentEvent.Source.WEBHOOK, event_type="stripe.unmatched",
                outcome=PaymentEvent.Outcome.IGNORED, request_id=request_id,
            )
            return Response({"received": True, "matched": False})

        reference_ok = bool(order.provider_reference) and str(order.provider_reference) == str(obj.get("id"))
        metadata = obj.get("metadata") or {}
        user_ok = not metadata.get("user_id") or str(metadata.get("user_id")) == str(order.user_id)
        if not reference_ok or not user_ok:
            open_issue(
                order, PaymentIssue.IssueType.REFERENCE_MISMATCH,
                severity=PaymentIssue.Severity.CRITICAL,
                message="Le webhook Stripe ne correspond pas à la session/utilisateur attendu.",
                expected={"reference": order.provider_reference, "user_id": order.user_id},
                observed={"reference": obj.get("id"), "user_id": metadata.get("user_id")},
            )
            record_event(
                order=order, source=PaymentEvent.Source.WEBHOOK, event_type="stripe.reference_mismatch",
                outcome=PaymentEvent.Outcome.REJECTED, request_id=request_id,
            )
            return Response({"received": True, "matched": False})

        if event_type == "checkout.session.completed":
            paid = str(obj.get("payment_status") or "").lower() == "paid"
            verification = {
                "paid": paid,
                "amount": _from_minor_units(obj.get("amount_total") or 0, order.currency),
                "currency": str(obj.get("currency") or "").upper(),
                "status": str(obj.get("payment_status") or "").upper(),
                "payment_method": "card",
            }
            classification = classify_verification(order, verification)
            if classification == "paid":
                with transaction.atomic():
                    locked = Order.objects.select_for_update().get(pk=order.pk)
                    CheckoutView()._fulfill(locked)
                resolve_order_issues(order, (PaymentIssue.IssueType.REFERENCE_MISMATCH,), "Webhook Stripe cohérent.")
                record_event(
                    order=order, source=PaymentEvent.Source.WEBHOOK, event_type="stripe.paid",
                    outcome=PaymentEvent.Outcome.ACCEPTED, request_id=request_id,
                )
            elif classification in {"amount_mismatch", "currency_mismatch"}:
                record_event(
                    order=order, source=PaymentEvent.Source.WEBHOOK, event_type="stripe.financial_mismatch",
                    outcome=PaymentEvent.Outcome.REJECTED, request_id=request_id,
                    payload={"classification": classification},
                )
        elif event_type in {"checkout.session.expired", "checkout.session.async_payment_failed"}:
            with transaction.atomic():
                locked = Order.objects.select_for_update().filter(pk=order.pk, status=Order.Status.PENDING).first()
                if locked:
                    locked.status = Order.Status.FAILED
                    locked.provider_status = event_type.upper()[:80]
                    locked.last_provider_check_at = timezone.now()
                    locked.save(update_fields=["status", "provider_status", "last_provider_check_at"])
                    mark_attempt_failed(locked, provider_status=event_type, message="Session Stripe expirée ou paiement asynchrone échoué.")
                    _release_failed_order_reservations(locked)
            record_event(
                order=order, source=PaymentEvent.Source.WEBHOOK, event_type="stripe.failed",
                outcome=PaymentEvent.Outcome.ACCEPTED, request_id=request_id,
                payload={"stripe_event": event_type},
            )
        else:
            record_event(
                order=order, source=PaymentEvent.Source.WEBHOOK, event_type="stripe.ignored_event",
                outcome=PaymentEvent.Outcome.IGNORED, request_id=request_id,
                payload={"stripe_event": event_type},
            )
        return Response({"received": True})

