from decimal import Decimal
from unittest.mock import patch

from django.test import override_settings
from django.core import mail

from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.catalog.models import Category, Course
from apps.enrollments.models import CourseEnrollment
from apps.formations.models import InteractiveFormation
from .models import Order, OrderItem, FormationSeatReservation, Currency, PaymentGateway
from .providers import _to_minor_units, _from_minor_units


class PaymentAccessRegressionTests(APITestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username="seller", email="seller@example.com", password="passpass123", role=User.Role.INSTRUCTOR
        )
        self.student = User.objects.create_user(
            username="buyer", email="buyer@example.com", password="passpass123", role=User.Role.STUDENT
        )
        category = Category.objects.create(name="Business")
        self.course = Course.objects.create(
            instructor=self.instructor,
            category=category,
            title="Cours payant",
            description="Test",
            price=Decimal("100.00"),
            published=True,
        )
        self.client.force_authenticate(self.student)
        Currency.objects.update_or_create(
            code="EUR",
            defaults={"name": "Euro", "symbol": "€", "exchange_rate": Decimal("1"), "decimal_places": 2, "is_active": True, "is_default": True},
        )
        Currency.objects.update_or_create(
            code="MAD",
            defaults={"name": "Dirham marocain", "symbol": "MAD", "exchange_rate": Decimal("10.87"), "decimal_places": 2, "is_active": True, "is_default": False},
        )
        PaymentGateway.objects.update_or_create(
            code="stripe",
            defaults={"name": "Stripe", "is_active": True, "supported_currencies": ["EUR", "MAD"], "sandbox": True},
        )

    @override_settings(STRIPE_SECRET_KEY="sk_test_fake")
    @patch("apps.payments.views.verify_payment")
    @patch("apps.payments.views.create_checkout")
    def test_confirmed_purchase_creates_access_and_finance_snapshot(self, create_checkout_mock, verify_payment_mock):
        create_checkout_mock.return_value = ("https://checkout.stripe.test/session", "cs_test_123")
        verify_payment_mock.return_value = {"paid": True, "amount": Decimal("100.00"), "currency": "EUR"}
        checkout = self.client.post(
            "/api/payments/checkout/",
            {"course_ids": [self.course.id], "pdf_ids": [], "formation_ids": [], "provider": "stripe"},
            format="json",
        )
        self.assertEqual(checkout.status_code, status.HTTP_201_CREATED, checkout.data)
        order_id = checkout.data["order"]["id"]
        confirm = self.client.post(f"/api/payments/orders/{order_id}/confirm/", {}, format="json")
        self.assertEqual(confirm.status_code, status.HTTP_200_OK, confirm.data)
        self.assertTrue(CourseEnrollment.objects.filter(user=self.student, course=self.course).exists())
        item = OrderItem.objects.get(order_id=order_id)
        self.assertEqual(item.instructor, self.instructor)
        self.assertEqual(item.platform_fee_amount, Decimal("15.00"))
        self.assertEqual(item.instructor_earning_amount, Decimal("85.00"))
        self.assertEqual(Order.objects.get(id=order_id).status, Order.Status.PAID)

        detail = self.client.get(f"/api/catalog/courses/{self.course.slug}/")
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertTrue(detail.data["is_enrolled"])
    def test_paid_order_reconciliation_repairs_missing_enrollment(self):
        order = Order.objects.create(
            user=self.student, status=Order.Status.PAID, total_amount=Decimal("100.00")
        )
        OrderItem.objects.create(
            order=order, item_type=OrderItem.ItemType.COURSE, course=self.course,
            instructor=self.instructor, unit_price=Decimal("100.00"),
            platform_fee_amount=Decimal("15.00"), instructor_earning_amount=Decimal("85.00"),
        )
        self.assertFalse(CourseEnrollment.objects.filter(user=self.student, course=self.course).exists())

        response = self.client.post(f"/api/payments/orders/{order.id}/confirm/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(CourseEnrollment.objects.filter(user=self.student, course=self.course).exists())

    @override_settings(TEST_PAYMENTS_ENABLED=True)
    def test_internal_test_payment_fulfills_paid_course_without_gateway_keys(self):
        PaymentGateway.objects.filter(code="manual").delete()
        response = self.client.post(
            "/api/payments/checkout/",
            {
                "course_ids": [self.course.id],
                "pdf_ids": [],
                "formation_ids": [],
                "provider": "manual",
                "currency": "EUR",
                "test_payment": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(response.data["test_payment"])
        self.assertFalse(response.data["manual_review"])
        order = Order.objects.get(pk=response.data["order"]["id"])
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertTrue(order.provider_sandbox)
        self.assertTrue(CourseEnrollment.objects.filter(user=self.student, course=self.course).exists())

    @override_settings(TEST_PAYMENTS_ENABLED=False)
    def test_internal_test_payment_is_rejected_when_disabled(self):
        response = self.client.post(
            "/api/payments/checkout/",
            {
                "course_ids": [self.course.id],
                "pdf_ids": [],
                "formation_ids": [],
                "provider": "manual",
                "currency": "EUR",
                "test_payment": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)
        self.assertFalse(CourseEnrollment.objects.filter(user=self.student, course=self.course).exists())

    def test_checkout_does_not_charge_owned_course_again(self):
        CourseEnrollment.objects.create(user=self.student, course=self.course)
        response = self.client.post(
            "/api/payments/checkout/",
            {"course_ids": [self.course.id], "pdf_ids": [], "formation_ids": [], "provider": "stripe"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("déjà", response.data["detail"])



    def test_free_course_with_stale_price_is_not_charged(self):
        self.course.is_free = True
        self.course.price = Decimal("100.00")
        self.course.save(update_fields=["is_free", "price"])
        response = self.client.post(
            "/api/payments/checkout/",
            {"course_ids": [self.course.id], "pdf_ids": [], "formation_ids": [], "provider": "stripe"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        order = Order.objects.get(pk=response.data["order"]["id"])
        self.assertEqual(order.total_amount, Decimal("0.00"))
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertTrue(CourseEnrollment.objects.filter(user=self.student, course=self.course).exists())

    @override_settings(STRIPE_SECRET_KEY="sk_test_fake")
    @patch("apps.payments.views.create_checkout")
    def test_paid_live_checkout_reserves_last_seat(self, create_checkout_mock):
        create_checkout_mock.return_value = ("https://checkout.stripe.test/live", "cs_live_1")
        formation = InteractiveFormation.objects.create(
            instructor=self.instructor, category=self.course.category, title="Live limité",
            description="Test", price=Decimal("50.00"), max_students=1, published=True,
        )
        response = self.client.post(
            "/api/payments/checkout/",
            {"course_ids": [], "pdf_ids": [], "formation_ids": [formation.id], "provider": "stripe"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(FormationSeatReservation.objects.filter(formation=formation, user=self.student).exists())

        second = User.objects.create_user(
            username="buyer2", email="buyer2@example.com", password="passpass123", role=User.Role.STUDENT
        )
        self.client.force_authenticate(second)
        blocked = self.client.post(
            "/api/payments/checkout/",
            {"course_ids": [], "pdf_ids": [], "formation_ids": [formation.id], "provider": "stripe"},
            format="json",
        )
        self.assertEqual(blocked.status_code, status.HTTP_409_CONFLICT, blocked.data)

    @override_settings(DEBUG=False)
    def test_admin_cannot_mark_unverified_paid_order_as_paid_in_production(self):
        admin = User.objects.create_user(
            username="pay_admin", email="pay-admin@example.com", password="passpass123", role=User.Role.ADMIN
        )
        order = Order.objects.create(user=self.student, total_amount=Decimal("100.00"), provider=Order.Provider.STRIPE)
        self.client.force_authenticate(admin)
        response = self.client.post(
            f"/api/payments/orders/{order.id}/set_status/", {"status": Order.Status.PAID}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)


class PaymentConfigurationTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="payment_admin", email="payment-admin@example.com", password="passpass123", role=User.Role.ADMIN
        )
        self.client.force_authenticate(self.admin)
        Currency.objects.update_or_create(
            code="EUR",
            defaults={"name": "Euro", "symbol": "€", "exchange_rate": Decimal("1"), "decimal_places": 2, "is_active": True, "is_default": True},
        )
        Currency.objects.update_or_create(
            code="MAD",
            defaults={"name": "Dirham marocain", "symbol": "MAD", "exchange_rate": Decimal("10.87"), "decimal_places": 2, "is_active": True, "is_default": False},
        )

    def test_admin_can_add_and_remove_unused_supported_gateway(self):
        created = self.client.post(
            "/api/payments/admin/gateways/",
            {"code": "youcanpay", "name": "YouCan Pay", "description": "Maroc", "is_active": False, "sandbox": True, "supported_currencies": ["MAD"], "sort_order": 10},
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
        deleted = self.client.delete(f"/api/payments/admin/gateways/{created.data['id']}/")
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)

    def test_gateway_rejects_unknown_currency(self):
        response = self.client.post(
            "/api/payments/admin/gateways/",
            {"code": "geniuspay", "name": "GeniusPay", "is_active": False, "sandbox": True, "supported_currencies": ["ZZZ"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("supported_currencies", response.data)

    def test_currency_precision_matches_order_storage(self):
        response = self.client.post(
            "/api/payments/admin/currencies/",
            {"code": "TST", "name": "Test", "symbol": "T", "exchange_rate": "1.0", "decimal_places": 3, "is_active": True, "is_default": False},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("decimal_places", response.data)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", DEFAULT_FROM_EMAIL="LearnEas <no-reply@example.com>")
    def test_admin_can_test_email_configuration(self):
        response = self.client.post("/api/payments/admin/test-email/", {"email": "diagnostic@example.com"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["diagnostic@example.com"])

    @patch("apps.payments.views.test_provider")
    def test_admin_can_run_gateway_diagnostic(self, test_provider_mock):
        gateway = PaymentGateway.objects.create(
            code="youcanpay", name="YouCan Pay", is_active=False, sandbox=True, supported_currencies=["MAD"]
        )
        test_provider_mock.return_value = {"ok": True, "detail": "Connexion valide."}
        response = self.client.post(f"/api/payments/admin/gateways/{gateway.id}/test/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(response.data["ok"])

    def test_eur_accounting_base_cannot_be_disabled_or_rerated(self):
        eur = Currency.objects.get(code="EUR")
        disabled = self.client.patch(f"/api/payments/admin/currencies/{eur.id}/", {"is_active": False}, format="json")
        self.assertEqual(disabled.status_code, status.HTTP_400_BAD_REQUEST, disabled.data)
        rerated = self.client.patch(f"/api/payments/admin/currencies/{eur.id}/", {"exchange_rate": "2"}, format="json")
        self.assertEqual(rerated.status_code, status.HTTP_400_BAD_REQUEST, rerated.data)
        deleted = self.client.delete(f"/api/payments/admin/currencies/{eur.id}/")
        self.assertEqual(deleted.status_code, status.HTTP_409_CONFLICT, deleted.data)

    def test_minor_unit_conversion_respects_currency_precision(self):
        Currency.objects.create(
            code="XOF", name="Franc CFA", symbol="F CFA", exchange_rate=Decimal("65"),
            decimal_places=0, is_active=True,
        )
        self.assertEqual(_to_minor_units(Decimal("15000"), "XOF"), 15000)
        self.assertEqual(_from_minor_units(15000, "XOF"), Decimal("15000"))
        self.assertEqual(_to_minor_units(Decimal("123.45"), "MAD"), 12345)
        self.assertEqual(_from_minor_units(12345, "MAD"), Decimal("123.45"))

