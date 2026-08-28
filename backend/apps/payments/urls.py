from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import (
    OrderViewSet, CheckoutView, ConfirmPaymentView, PayoutProfileView,
    InstructorFinanceView, InstructorPayoutViewSet, AdminOverviewView,
)

router = DefaultRouter()
router.register("orders", OrderViewSet, basename="order")
router.register("payouts", InstructorPayoutViewSet, basename="payout")

urlpatterns = router.urls + [
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("orders/<int:order_id>/confirm/", ConfirmPaymentView.as_view(), name="confirm-payment"),
    path("instructor/finance/", InstructorFinanceView.as_view(), name="instructor-finance"),
    path("instructor/payout-profile/", PayoutProfileView.as_view(), name="payout-profile"),
    path("admin/overview/", AdminOverviewView.as_view(), name="admin-overview"),
]
