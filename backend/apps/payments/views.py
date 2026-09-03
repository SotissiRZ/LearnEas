from decimal import Decimal, ROUND_HALF_UP
import logging
import hashlib
import hmac
import json
import time
from datetime import timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.cache import cache
from django.http import HttpResponseRedirect
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
from apps.formations.models import InteractiveFormation, FormationEnrollment, FormationSession, FormationAttendance, MentorshipBooking, FormationKind
from .models import Order, OrderItem, PayoutProfile, InstructorPayout, FormationSeatReservation, Currency, PaymentGateway
import stripe
from apps.common.throttles import CheckoutRateThrottle, AdminTestRateThrottle, WebhookRateThrottle

from .serializers import (
    OrderSerializer, CheckoutSerializer, PayoutProfileSerializer, InstructorPayoutSerializer,
    CurrencySerializer, PaymentGatewaySerializer,
)
from .providers import (
    ProviderError, create_checkout, test_provider, verify_payment, is_configured,
    _from_minor_units, normalize_provider_amount, _cinetpay_config,
)

logger = logging.getLogger(__name__)

MONEY = Decimal("0.01")


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


def _split_revenue(price):
    commission_percent, _ = _platform_finance_settings()
    pct = commission_percent / Decimal("100")
    price = Decimal(price)
    fee = (price * pct).quantize(MONEY, rounding=ROUND_HALF_UP)
    return fee, (price - fee).quantize(MONEY, rounding=ROUND_HALF_UP)


def _release_failed_order_reservations(order):
    """Libère uniquement les réservations liées à une commande définitivement échouée.

    Une commande encore PENDING peut être confirmée de façon asynchrone par Mobile Money
    ou carte : elle ne doit donc jamais libérer un créneau de mentorat ou une place de cohorte.
    """
    FormationSeatReservation.objects.filter(order=order).delete()
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
    earnings = paid_items.aggregate(v=Sum("instructor_earning_amount"))["v"] or Decimal("0")
    locked = InstructorPayout.objects.filter(
        instructor=instructor,
        status__in=[InstructorPayout.Status.PENDING, InstructorPayout.Status.PROCESSING, InstructorPayout.Status.PAID],
    ).aggregate(v=Sum("amount"))["v"] or Decimal("0")
    paid_out = InstructorPayout.objects.filter(
        instructor=instructor, status=InstructorPayout.Status.PAID
    ).aggregate(v=Sum("amount"))["v"] or Decimal("0")
    return {
        "gross_revenue": gross,
        "total_earnings": earnings,
        "available_balance": max(earnings - locked, Decimal("0")),
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
        qs = Order.objects.select_related("user").prefetch_related("items__instructor", "items__course", "items__pdf_product", "items__formation", "items__mentorship_booking__offering")
        if user.role == "admin":
            return qs
        return qs.filter(user=user)

    @action(detail=True, methods=["post"], permission_classes=[IsAdminRole])
    def set_status(self, request, pk=None):
        order = self.get_object()
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
        if new_status not in allowed.get(order.status, set()):
            return Response({"detail": "Transition de statut invalide."}, status=409)
        if new_status == Order.Status.PAID:
            if order.base_total_amount > 0 and order.provider != Order.Provider.MANUAL and not settings.DEBUG:
                return Response({"detail": "Seuls le webhook/contrôle du prestataire peuvent confirmer une commande externe."}, status=403)
            CheckoutView()._fulfill(order)
        else:
            order.status = new_status
            order.save(update_fields=["status"])
            if new_status == Order.Status.FAILED:
                _release_failed_order_reservations(order)
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
        test_payment = bool(data.get("test_payment"))
        if test_payment and not settings.TEST_PAYMENTS_ENABLED:
            return Response({"detail": "Les paiements de test sont désactivés sur cet environnement."}, status=403)

        currency = Currency.objects.filter(code=data["currency"], is_active=True).first()
        if not currency:
            return Response({"currency": ["Cette devise n'est pas active."]}, status=400)
        # La validation du prestataire est volontairement différée jusqu'au calcul du total :
        # un contenu gratuit ne doit jamais dépendre de la disponibilité d'une passerelle externe.
        gateway = PaymentGateway.objects.filter(code=data["provider"]).first()

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
        if not courses and not pdfs and not formations and not mentorship_bookings:
            return Response({"detail": "Tous les éléments du panier sont déjà acquis, expirés ou indisponibles."}, status=400)

        now = timezone.now()
        unavailable = []
        for formation in formations:
            active_reservations = FormationSeatReservation.objects.filter(formation=formation, order__status=Order.Status.PENDING, expires_at__gt=now).count()
            if not formation.is_enrollment_open or formation.enrollments.count() + active_reservations >= formation.max_students:
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

        base_total = sum((Decimal("0") if c.is_free else (c.discount_price if c.discount_price is not None else c.price) for c in courses), Decimal("0"))
        base_total += sum((Decimal("0") if item.is_free else item.price for item in pdfs), Decimal("0"))
        base_total += sum((item.price for item in formations), Decimal("0"))
        base_total += sum((item.price_snapshot for item in mentorship_bookings), Decimal("0"))
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

        order = Order.objects.create(
            user=user,
            provider=provider_code,
            provider_sandbox=bool(test_payment or (gateway.sandbox if base_total > 0 and gateway else False)),
            base_total_amount=base_total,
            total_amount=payment_total,
            currency=currency.code,
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
        mentorship_payment_expiry = timezone.now() + timedelta(hours=2)
        for booking in mentorship_bookings:
            # Une fois le checkout lancé, le créneau reste bloqué assez longtemps pour
            # couvrir les wallets Mobile Money dont la confirmation peut être différée.
            booking.expires_at = mentorship_payment_expiry
            booking.save(update_fields=["expires_at", "updated_at"])
            fee, earning = _split_revenue(booking.price_snapshot)
            OrderItem.objects.create(
                order=order,
                item_type=OrderItem.ItemType.MENTORING,
                mentorship_booking=booking,
                instructor=booking.offering.instructor,
                unit_price=booking.price_snapshot,
                platform_fee_amount=fee,
                instructor_earning_amount=earning,
            )

        if base_total > 0:
            reservation_expiry = timezone.now() + timedelta(minutes=45)
            for formation in formations:
                FormationSeatReservation.objects.create(order=order, formation=formation, user=user, expires_at=reservation_expiry)

        if base_total == 0 or test_payment:
            self._fulfill(order)
            checkout_url = None
        elif provider_code == Order.Provider.MANUAL:
            checkout_url = None
        else:
            try:
                checkout_url, reference = create_checkout(order, user)
            except ProviderError as exc:
                transaction.set_rollback(True)
                return Response({"provider": [str(exc)]}, status=502)
            order.provider_reference = reference
            order.save(update_fields=["provider_reference"])

        return Response({
            "order": OrderSerializer(order).data,
            "requires_payment": base_total > 0,
            "checkout_url": checkout_url,
            "manual_review": bool(base_total > 0 and provider_code == Order.Provider.MANUAL and not test_payment),
            "test_payment": test_payment,
        }, status=201)

    def _fulfill(self, order):
        if order.status != Order.Status.PAID:
            order.status = Order.Status.PAID
            order.paid_at = timezone.now()
            order.save(update_fields=["status", "paid_at"])
        elif not order.paid_at:
            order.paid_at = timezone.now()
            order.save(update_fields=["paid_at"])
        for item in order.items.select_related("course", "pdf_product", "formation", "mentorship_booking__offering", "mentorship_booking__slot").all():
            if item.course:
                CourseEnrollment.objects.get_or_create(user=order.user, course=item.course)
                item.course.students_count = item.course.enrollments.count()
                item.course.save(update_fields=["students_count"])
            if item.pdf_product:
                purchase, created = PDFPurchase.objects.get_or_create(user=order.user, pdf_product=item.pdf_product)
                if created:
                    item.pdf_product.downloads_count += 1
                    item.pdf_product.save(update_fields=["downloads_count"])
            if item.formation:
                formation = InteractiveFormation.objects.select_for_update().get(pk=item.formation_id)
                if not FormationEnrollment.objects.filter(user=order.user, formation=formation).exists():
                    now = timezone.now()
                    reservation = FormationSeatReservation.objects.filter(order=order, formation=formation).first()
                    reservation_valid = bool(reservation and reservation.expires_at > now)
                    active_other = FormationSeatReservation.objects.filter(formation=formation, order__status=Order.Status.PENDING, expires_at__gt=now).exclude(order=order).count()
                    if formation.enrollments.count() + active_other >= formation.max_students and not reservation_valid:
                        raise ValueError(f"Plus de place disponible pour la formation {formation.title}.")
                    FormationEnrollment.objects.create(user=order.user, formation=formation)
            if item.mentorship_booking:
                from apps.formations.mentorship import confirm_booking
                confirm_booking(item.mentorship_booking)
        FormationSeatReservation.objects.filter(order=order).delete()
        # La notification est lancée après COMMIT afin qu'une panne WhatsApp ne puisse jamais
        # invalider une commande déjà payée et que le worker voie les inscriptions créées.
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
        order = Order.objects.select_for_update().filter(id=order_id, user=request.user).first()
        if not order:
            return Response({"detail": "Commande introuvable."}, status=404)
        if order.status == Order.Status.PAID:
            return Response(OrderSerializer(order).data)
        if order.status == Order.Status.FAILED:
            return Response({"detail": "Cette commande a déjà échoué. Relancez un nouveau paiement."}, status=402)
        if order.base_total_amount == 0:
            CheckoutView()._fulfill(order)
        elif order.provider == Order.Provider.MANUAL:
            return Response({"detail": "Le paiement manuel doit être validé par un administrateur."}, status=409)
        elif settings.DEBUG and request.data.get("dev_force") is True:
            CheckoutView()._fulfill(order)
        else:
            try:
                verification = verify_payment(order)
            except ProviderError as exc:
                return Response({"detail": str(exc)}, status=502)
            expected = Decimal(order.total_amount)
            if not verification["paid"]:
                provider_status = str(verification.get("status") or "").upper()
                terminal_failures = {"CANCELLED", "CANCELED", "FAILED"}
                # CinetPay peut faire transiter certains wallets par REFUSED avant un autre
                # état opérateur ; on ne libère donc jamais le créneau sur ce seul statut.
                if provider_status == "REFUSED" and order.provider != Order.Provider.CINETPAY:
                    terminal_failures.add("REFUSED")
                if provider_status in terminal_failures:
                    order.status = Order.Status.FAILED
                    order.save(update_fields=["status"])
                    _release_failed_order_reservations(order)
                    return Response({"detail": "Le paiement a été refusé ou annulé par le prestataire."}, status=402)
                return Response({"detail": "Le paiement est encore en attente de confirmation par le prestataire."}, status=409)
            if verification["currency"] != order.currency or abs(Decimal(verification["amount"]) - expected) > Decimal("0.01"):
                return Response({"detail": "Le montant ou la devise confirmée par le prestataire ne correspond pas à la commande."}, status=409)
            CheckoutView()._fulfill(order)
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
        ).select_related("order", "course", "pdf_product", "formation", "mentorship_booking__offering").order_by("-order__paid_at")[:10]
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
        for item_type in (OrderItem.ItemType.COURSE, OrderItem.ItemType.PDF, OrderItem.ItemType.FORMATION, OrderItem.ItemType.MENTORING):
            field = {
                OrderItem.ItemType.COURSE: "course__title",
                OrderItem.ItemType.PDF: "pdf_product__title",
                OrderItem.ItemType.FORMATION: "formation__title",
                OrderItem.ItemType.MENTORING: "mentorship_booking__offering__title",
            }[item_type]
            id_field = {
                OrderItem.ItemType.COURSE: "course_id",
                OrderItem.ItemType.PDF: "pdf_product_id",
                OrderItem.ItemType.FORMATION: "formation_id",
                OrderItem.ItemType.MENTORING: "mentorship_booking__offering_id",
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
                    "title": item.course.title if item.course else item.pdf_product.title if item.pdf_product else item.formation.title if item.formation else item.mentorship_booking.offering.title if item.mentorship_booking else "",
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
    def mark_paid(self, request, pk=None):
        payout = self.get_object()
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
            "instructors": User.objects.filter(role=User.Role.INSTRUCTOR).count(),
            "pending_instructor_applications": InstructorApplication.objects.filter(status=InstructorApplication.Status.PENDING).count(),
            "courses": Course.objects.count(),
            "pdfs": PDFProduct.objects.count(),
            "formations": InteractiveFormation.objects.count(),
            "orders": Order.objects.count(),
            "paid_orders": paid_orders.count(),
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
            sent = send_mail(
                subject="Test email LearnEas",
                message="Votre configuration email LearnEas fonctionne correctement.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
        except Exception:
            logger.exception("Échec du diagnostic email LearnEas")
            return Response({"ok": False, "detail": "Échec du test email. Consultez les journaux serveur pour le détail technique."}, status=400)
        return Response({"ok": bool(sent), "detail": f"Email de test envoyé à {recipient}."})


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
    """Notification serveur CinetPay.

    La notification est authentifiée par X-TOKEN/HMAC puis la transaction est
    systématiquement relue via l'API CinetPay avant de délivrer le contenu.
    CinetPay peut appeler plusieurs fois cette URL : le traitement est idempotent.
    """
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
        # CinetPay ping l'URL en GET lors de certains diagnostics.
        return Response({"received": True})

    def _valid_hmac(self, request, secret_key: str) -> bool:
        received = request.META.get("HTTP_X_TOKEN", "")
        if not received or not secret_key:
            return False
        data = "".join(str(request.data.get(field) or "") for field in self._hmac_fields)
        expected = hmac.new(secret_key.encode("utf-8"), data.encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected.lower(), str(received).lower())

    def post(self, request):
        transaction_id = str(request.data.get("cpm_trans_id") or "").strip()
        site_id = str(request.data.get("cpm_site_id") or "").strip()
        if not transaction_id or not site_id:
            return Response({"detail": "Notification CinetPay incomplète."}, status=400)

        # Déterminer l'environnement uniquement à partir du site_id attendu + HMAC.
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
        if not order:
            # Réponse 200 pour une notification authentique mais inconnue : CinetPay ne doit
            # pas boucler indéfiniment sur une ancienne transaction d'un autre environnement.
            return Response({"received": True, "matched": False})
        if order.status == Order.Status.PAID:
            return Response({"received": True, "paid": True, "duplicate": True})

        try:
            verification = verify_payment(order)
        except ProviderError:
            logger.exception("Échec de vérification CinetPay pour la commande %s", order.id)
            return Response({"detail": "Vérification CinetPay temporairement indisponible."}, status=502)

        if verification.get("paid"):
            amount_ok = abs(Decimal(verification.get("amount", 0)) - Decimal(order.total_amount)) <= Decimal("0.01")
            currency_ok = str(verification.get("currency") or "").upper() == order.currency
            if amount_ok and currency_ok:
                with transaction.atomic():
                    locked = Order.objects.select_for_update().get(pk=order.pk)
                    if locked.status != Order.Status.PAID:
                        CheckoutView()._fulfill(locked)
                return Response({"received": True, "paid": True})
            logger.warning("CinetPay mismatch order=%s amount_ok=%s currency_ok=%s", order.id, amount_ok, currency_ok)
            return Response({"detail": "Montant ou devise CinetPay incohérent."}, status=409)

        # WAITING_FOR_CUSTOMER/REFUSED restent non délivrés. On ne marque pas FAILED ici :
        # certains opérateurs notifient plusieurs états avant la confirmation finale.
        return Response({"received": True, "paid": False, "status": verification.get("status", "")})


class GeniusPayWebhookView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [WebhookRateThrottle]

    def post(self, request):
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

        replay_key = f"geniuspay:webhook:{hashlib.sha256((timestamp + ':' + signature).encode()).hexdigest()}"
        if not cache.add(replay_key, True, timeout=310):
            return Response({"received": True, "duplicate": True})
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except Exception:
            return Response({"detail": "JSON invalide."}, status=400)
        payload_environment = str(payload.get("environment") or "").strip().lower()
        expected_environment = "sandbox" if sandbox_event else "live"
        if payload_environment and payload_environment != expected_environment:
            return Response({"detail": "Environnement webhook GeniusPay incohérent."}, status=400)
        if event_name == "payment.success" or payload.get("event") == "payment.success":
            data = payload.get("data") or {}
            metadata = data.get("metadata") or {}
            order_id = metadata.get("order_id")
            if order_id:
                with transaction.atomic():
                    order = Order.objects.select_for_update().filter(
                        pk=order_id,
                        provider=Order.Provider.GENIUSPAY,
                        provider_sandbox=bool(sandbox_event),
                    ).first()
                    if order:
                        amount = Decimal(str(data.get("amount", "0")))
                        currency = str(data.get("currency") or "").upper()
                        reference = str(data.get("reference") or data.get("id") or "")
                        user_ok = str(metadata.get("user_id") or "") == str(order.user_id)
                        reference_ok = bool(order.provider_reference) and reference == str(order.provider_reference)
                        if user_ok and reference_ok and currency == order.currency and abs(amount - Decimal(order.total_amount)) <= Decimal("0.01"):
                            CheckoutView()._fulfill(order)
        return Response({"received": True})


class StripeWebhookView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [WebhookRateThrottle]

    def post(self, request):
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
        event_type = event.get("type")
        if event_type == "checkout.session.completed":
            obj = event["data"]["object"]
            order_id = (obj.get("metadata") or {}).get("order_id") or obj.get("client_reference_id")
            if order_id:
                with transaction.atomic():
                    order = Order.objects.select_for_update().filter(pk=order_id, provider=Order.Provider.STRIPE, provider_sandbox=bool(webhook_sandbox)).first()
                    if order and str(order.provider_reference) == str(obj.get("id")):
                        amount = _from_minor_units(obj.get("amount_total") or 0, order.currency)
                        currency = str(obj.get("currency") or "").upper()
                        metadata = obj.get("metadata") or {}
                        user_ok = str(metadata.get("user_id") or "") == str(order.user_id)
                        paid = str(obj.get("payment_status") or "").lower() == "paid"
                        if paid and user_ok and currency == order.currency and abs(amount - Decimal(order.total_amount)) <= Decimal("0.01"):
                            CheckoutView()._fulfill(order)
        elif event_type in {"checkout.session.expired", "checkout.session.async_payment_failed"}:
            obj = event["data"]["object"]
            order_id = (obj.get("metadata") or {}).get("order_id") or obj.get("client_reference_id")
            if order_id:
                with transaction.atomic():
                    order = Order.objects.select_for_update().filter(
                        pk=order_id, provider=Order.Provider.STRIPE, provider_sandbox=bool(webhook_sandbox),
                        status=Order.Status.PENDING,
                    ).first()
                    if order and str(order.provider_reference) == str(obj.get("id")):
                        order.status = Order.Status.FAILED
                        order.save(update_fields=["status"])
                        _release_failed_order_reservations(order)
        return Response({"received": True})
