from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import OrderViewSet, CheckoutView, ConfirmPaymentView

router = DefaultRouter()
router.register("orders", OrderViewSet, basename="order")

urlpatterns = router.urls + [
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("orders/<int:order_id>/confirm/", ConfirmPaymentView.as_view(), name="confirm-payment"),
]
