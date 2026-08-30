from decimal import Decimal, ROUND_HALF_UP
from datetime import timedelta
from django.conf import settings
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
from apps.formations.models import InteractiveFormation, FormationEnrollment, FormationSession, FormationAttendance
from .models import Order, OrderItem, PayoutProfile, InstructorPayout, FormationSeatReservation
import stripe
from apps.common.throttles import CheckoutRateThrottle

from .serializers import (
    OrderSerializer, CheckoutSerializer, PayoutProfileSerializer, InstructorPayoutSerializer,
)

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
        qs = Order.objects.select_related("user").prefetch_related("items__instructor", "items__course", "items__pdf_product", "items__formation")
        if user.role == "admin":
            return qs
        return qs.filter(user=user)

    @action(detail=True, methods=["post"], permission_classes=[IsAdminRole])
    def set_status(self, request, pk=None):
        order = self.get_object()
        new_status = request.data.get("status")
        if new_status not in Order.Status.values:
            return Response({"status": ["Statut invalide."]}, status=400)
        if new_status == Order.Status.PAID:
            if order.status != Order.Status.PAID and order.total_amount > 0 and not settings.DEBUG:
                return Response(
                    {"detail": "Une commande payante ne peut être marquée payée sans confirmation du prestataire."},
                    status=403,
                )
            CheckoutView()._fulfill(order)
        else:
            order.status = new_status
            order.save(update_fields=["status"])
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

        # Ne jamais refacturer un contenu déjà acquis. Les formations sont verrouillées
        # pendant le checkout afin d'éviter que deux paiements prennent la dernière place.
        owned_course_ids = set(CourseEnrollment.objects.filter(user=user).values_list("course_id", flat=True))
        owned_pdf_ids = set(PDFPurchase.objects.filter(user=user).values_list("pdf_product_id", flat=True))
        owned_formation_ids = set(FormationEnrollment.objects.filter(user=user).values_list("formation_id", flat=True))

        courses = Course.objects.filter(
            id__in=[pk for pk in data["course_ids"] if pk not in owned_course_ids], published=True
        )
        pdfs = PDFProduct.objects.filter(
            id__in=[pk for pk in data["pdf_ids"] if pk not in owned_pdf_ids], published=True
        )
        formations = InteractiveFormation.objects.select_for_update().filter(
            id__in=[pk for pk in data["formation_ids"] if pk not in owned_formation_ids], published=True
        )

        if not courses.exists() and not pdfs.exists() and not formations.exists():
            return Response(
                {"detail": "Tous les éléments du panier sont déjà dans votre bibliothèque ou ne sont plus disponibles."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        unavailable = []
        for formation in formations:
            active_reservations = FormationSeatReservation.objects.filter(
                formation=formation, order__status=Order.Status.PENDING, expires_at__gt=now
            ).count()
            if formation.enrollments.count() + active_reservations >= formation.max_students:
                unavailable.append(formation.title)
        if unavailable:
            return Response(
                {"detail": "Formation(s) complète(s) ou temporairement réservée(s) : " + ", ".join(unavailable)},
                status=status.HTTP_409_CONFLICT,
            )

        course_prices = [Decimal("0") if c.is_free else (c.discount_price if c.discount_price is not None else c.price) for c in courses]
        pdf_prices = [Decimal("0") if p.is_free else p.price for p in pdfs]
        formation_prices = [f.price for f in formations]
        total = sum(course_prices, Decimal("0")) + sum(pdf_prices, Decimal("0")) + sum(formation_prices, Decimal("0"))

        order = Order.objects.create(user=user, provider=data["provider"], total_amount=total)
        for c in courses:
            price = Decimal("0") if c.is_free else (c.discount_price if c.discount_price is not None else c.price)
            fee, earning = _split_revenue(price)
            OrderItem.objects.create(
                order=order, item_type=OrderItem.ItemType.COURSE, course=c, instructor=c.instructor,
                unit_price=price, platform_fee_amount=fee, instructor_earning_amount=earning,
            )
        for p in pdfs:
            price = Decimal("0") if p.is_free else p.price
            fee, earning = _split_revenue(price)
            OrderItem.objects.create(
                order=order, item_type=OrderItem.ItemType.PDF, pdf_product=p, instructor=p.instructor,
                unit_price=price, platform_fee_amount=fee, instructor_earning_amount=earning,
            )
        for f in formations:
            fee, earning = _split_revenue(f.price)
            OrderItem.objects.create(
                order=order, item_type=OrderItem.ItemType.FORMATION, formation=f, instructor=f.instructor,
                unit_price=f.price, platform_fee_amount=fee, instructor_earning_amount=earning,
            )

        # Une commande payante réserve les places suffisamment longtemps pour couvrir
        # la fenêtre Stripe (30 min) et un léger délai de livraison du webhook.
        if total > 0:
            reservation_expiry = timezone.now() + timedelta(minutes=40)
            for f in formations:
                FormationSeatReservation.objects.create(
                    order=order, formation=f, user=user, expires_at=reservation_expiry
                )

        if total == 0:
            self._fulfill(order)

        checkout_url = None
        if total > 0:
            if data["provider"] != Order.Provider.STRIPE:
                return Response({"detail": "Ce moyen de paiement n'est pas encore activé."}, status=status.HTTP_400_BAD_REQUEST)
            if not settings.STRIPE_SECRET_KEY:
                return Response({"detail": "Stripe n'est pas configuré sur cette installation."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            stripe.api_key = settings.STRIPE_SECRET_KEY
            session = stripe.checkout.Session.create(
                mode="payment",
                line_items=[{
                    "price_data": {
                        "currency": getattr(settings, "PAYMENT_CURRENCY", "mad").lower(),
                        "product_data": {"name": f"Commande LearnEas {order.invoice_number}"},
                        "unit_amount": int((order.total_amount * 100).quantize(Decimal("1"))),
                    },
                    "quantity": 1,
                }],
                success_url=f"{settings.FRONTEND_URL}/dashboard/student?purchased=1&order={order.id}",
                cancel_url=f"{settings.FRONTEND_URL}/checkout?cancelled=1",
                client_reference_id=str(order.id),
                metadata={"order_id": str(order.id), "user_id": str(user.id)},
                expires_at=int((timezone.now() + timedelta(minutes=30)).timestamp()),
            )
            order.provider_reference = session.id
            order.save(update_fields=["provider_reference"])
            checkout_url = session.url

        return Response({
            "order": OrderSerializer(order).data,
            "requires_payment": total > 0,
            "checkout_url": checkout_url,
        }, status=status.HTTP_201_CREATED)

    def _fulfill(self, order):
        # Idempotent : même si la commande est déjà marquée payée, on réconcilie toujours
        # les droits d'accès. Cela répare notamment les anciennes commandes payées pour
        # lesquelles une inscription aurait manqué à la suite d'une erreur transitoire.
        if order.status != Order.Status.PAID:
            order.status = Order.Status.PAID
            order.paid_at = timezone.now()
            order.save(update_fields=["status", "paid_at"])
        elif not order.paid_at:
            order.paid_at = timezone.now()
            order.save(update_fields=["paid_at"])

        for item in order.items.select_related("course", "pdf_product", "formation").all():
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
                    active_other_reservations = FormationSeatReservation.objects.filter(
                        formation=formation, order__status=Order.Status.PENDING, expires_at__gt=now
                    ).exclude(order=order).count()
                    if formation.enrollments.count() + active_other_reservations >= formation.max_students and not reservation_valid:
                        raise ValueError(f"Plus de place disponible pour la formation {formation.title}.")
                    FormationEnrollment.objects.create(user=order.user, formation=formation)
        FormationSeatReservation.objects.filter(order=order).delete()
        return order


class ConfirmPaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, order_id):
        try:
            order = Order.objects.select_for_update().get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({"detail": "Commande introuvable."}, status=404)
        if order.total_amount > 0 and not settings.DEBUG:
            return Response({"detail": "Une commande payante est confirmée uniquement par le webhook du prestataire."}, status=403)
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
        ).select_related("order", "course", "pdf_product", "formation").order_by("-order__paid_at")[:10]
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
        for item_type in (OrderItem.ItemType.COURSE, OrderItem.ItemType.PDF, OrderItem.ItemType.FORMATION):
            field = {
                OrderItem.ItemType.COURSE: "course__title",
                OrderItem.ItemType.PDF: "pdf_product__title",
                OrderItem.ItemType.FORMATION: "formation__title",
            }[item_type]
            id_field = {
                OrderItem.ItemType.COURSE: "course_id",
                OrderItem.ItemType.PDF: "pdf_product_id",
                OrderItem.ItemType.FORMATION: "formation_id",
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
                    "title": item.course.title if item.course else item.pdf_product.title if item.pdf_product else item.formation.title if item.formation else "",
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
            return Response({"amount": [f"Le retrait minimum est de {minimum} MAD."]}, status=400)
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
        payout.status = InstructorPayout.Status.FAILED
        payout.processed_at = timezone.now()
        payout.note = request.data.get("note", "")
        payout.save(update_fields=["status", "processed_at", "note"])
        return Response(self.get_serializer(payout).data)


class AdminOverviewView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        paid_orders = Order.objects.filter(status=Order.Status.PAID)
        total_revenue = paid_orders.aggregate(v=Sum("total_amount"))["v"] or Decimal("0")
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


class StripeWebhookView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "")
        if not secret:
            return Response({"detail": "Webhook Stripe non configuré."}, status=503)
        try:
            event = stripe.Webhook.construct_event(request.body, request.META.get("HTTP_STRIPE_SIGNATURE", ""), secret)
        except Exception:
            return Response({"detail": "Signature webhook invalide."}, status=400)
        if event.get("type") == "checkout.session.completed":
            obj = event["data"]["object"]
            order_id = (obj.get("metadata") or {}).get("order_id") or obj.get("client_reference_id")
            if order_id:
                with transaction.atomic():
                    order = Order.objects.select_for_update().filter(pk=order_id, provider=Order.Provider.STRIPE).first()
                    if order and str(order.provider_reference) == str(obj.get("id")):
                        CheckoutView()._fulfill(order)
        return Response({"received": True})
