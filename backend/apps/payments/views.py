from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Course, PDFProduct
from apps.enrollments.models import CourseEnrollment, PDFPurchase
from .models import Order, OrderItem
from .serializers import OrderSerializer, CheckoutSerializer


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return Order.objects.all()
        return Order.objects.filter(user=user)


class CheckoutView(APIView):
    """
    Crée une commande (panier -> cours complets + pdfs) puis simule/route le paiement.
    En prod: intégrer réellement Stripe PaymentIntent / PayPal Orders API ici.
    """
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = request.user

        courses = Course.objects.filter(id__in=data["course_ids"], published=True)
        pdfs = PDFProduct.objects.filter(id__in=data["pdf_ids"], published=True)

        if not courses and not pdfs:
            return Response({"detail": "Panier vide."}, status=status.HTTP_400_BAD_REQUEST)

        total = sum((c.discount_price or c.price) for c in courses) + sum(p.price for p in pdfs)

        order = Order.objects.create(user=user, provider=data["provider"], total_amount=total)
        for c in courses:
            OrderItem.objects.create(
                order=order, item_type=OrderItem.ItemType.COURSE, course=c,
                unit_price=(c.discount_price or c.price),
            )
        for p in pdfs:
            OrderItem.objects.create(
                order=order, item_type=OrderItem.ItemType.PDF, pdf_product=p, unit_price=p.price,
            )

        # NOTE: en environnement réel, on renverrait ici un client_secret Stripe
        # ou une redirect_url PayPal, et la confirmation se ferait via webhook.
        # Pour ce scaffold, si le total est 0 (contenu gratuit) on valide directement.
        if total == 0:
            self._fulfill(order)

        return Response(
            {
                "order": OrderSerializer(order).data,
                "requires_payment": total > 0,
                "stripe_checkout_stub": total > 0,
            },
            status=status.HTTP_201_CREATED,
        )

    def _fulfill(self, order):
        order.status = Order.Status.PAID
        order.paid_at = timezone.now()
        order.save()
        for item in order.items.all():
            if item.course:
                enrollment, _ = CourseEnrollment.objects.get_or_create(user=order.user, course=item.course)
                item.course.students_count = item.course.enrollments.count()
                item.course.save(update_fields=["students_count"])
            if item.pdf_product:
                PDFPurchase.objects.get_or_create(user=order.user, pdf_product=item.pdf_product)
                item.pdf_product.downloads_count += 1
                item.pdf_product.save(update_fields=["downloads_count"])


class ConfirmPaymentView(APIView):
    """Endpoint appelé par le webhook Stripe/PayPal (ou en dev, manuellement)
    pour finaliser une commande en attente."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({"detail": "Commande introuvable."}, status=404)

        if order.status == Order.Status.PAID:
            return Response(OrderSerializer(order).data)

        checkout_view = CheckoutView()
        checkout_view._fulfill(order)
        return Response(OrderSerializer(order).data)
