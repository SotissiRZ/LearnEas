from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import (
    OrderViewSet, CheckoutView, ConfirmPaymentView, PremiumAccessView, PayoutProfileView,
    InstructorFinanceView, InstructorPayoutViewSet, AdminOverviewView, StripeWebhookView, GeniusPayWebhookView, CinetPayWebhookView, CinetPayReturnView, CurrencyViewSet, PaymentGatewayViewSet, PublicPaymentConfigView, AdminEmailTestView,
)

router = DefaultRouter()
router.register("orders", OrderViewSet, basename="order")
router.register("payouts", InstructorPayoutViewSet, basename="payout")
router.register("admin/currencies", CurrencyViewSet, basename="currency")
router.register("admin/gateways", PaymentGatewayViewSet, basename="gateway")

urlpatterns = router.urls + [
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("premium/", PremiumAccessView.as_view(), name="premium-access"),
    path("stripe/webhook/", StripeWebhookView.as_view(), name="stripe-webhook"),
    path("geniuspay/webhook/", GeniusPayWebhookView.as_view(), name="geniuspay-webhook"),
    path("cinetpay/webhook/", CinetPayWebhookView.as_view(), name="cinetpay-webhook"),
    path("cinetpay/return/", CinetPayReturnView.as_view(), name="cinetpay-return"),
    path("config/", PublicPaymentConfigView.as_view(), name="payment-config"),
    path("admin/test-email/", AdminEmailTestView.as_view(), name="admin-test-email"),
    path("orders/<int:order_id>/confirm/", ConfirmPaymentView.as_view(), name="confirm-payment"),
    path("instructor/finance/", InstructorFinanceView.as_view(), name="instructor-finance"),
    path("instructor/payout-profile/", PayoutProfileView.as_view(), name="payout-profile"),
    path("admin/overview/", AdminOverviewView.as_view(), name="admin-overview"),
]
