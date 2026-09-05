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
from .models import (
    Order, OrderItem, FormationSeatReservation, Currency, PaymentGateway, InstructorLedgerEntry,
    PaymentAttempt, PaymentEvent, PaymentIssue,
)
from .providers import _to_minor_units, _from_minor_units, normalize_provider_amount


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

    @override_settings(TEST_PAYMENTS_ENABLED=True)
    def test_checkout_idempotency_replays_same_order_without_duplicate_rights_or_ledger(self):
        payload = {
            "course_ids": [self.course.id], "pdf_ids": [], "formation_ids": [],
            "provider": "manual", "currency": "EUR", "test_payment": True,
        }
        first = self.client.post(
            "/api/payments/checkout/", payload, format="json", HTTP_IDEMPOTENCY_KEY="checkout-course-001"
        )
        second = self.client.post(
            "/api/payments/checkout/", payload, format="json", HTTP_IDEMPOTENCY_KEY="checkout-course-001"
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED, first.data)
        self.assertEqual(second.status_code, status.HTTP_200_OK, second.data)
        self.assertTrue(second.data["idempotent_replay"])
        self.assertEqual(first.data["order"]["id"], second.data["order"]["id"])
        self.assertEqual(Order.objects.filter(user=self.student).count(), 1)
        self.assertEqual(CourseEnrollment.objects.filter(user=self.student, course=self.course).count(), 1)
        self.assertEqual(
            InstructorLedgerEntry.objects.filter(entry_type=InstructorLedgerEntry.EntryType.SALE).count(), 1
        )

    @override_settings(TEST_PAYMENTS_ENABLED=True)
    def test_checkout_idempotency_key_rejects_different_payload(self):
        payload = {
            "course_ids": [self.course.id], "pdf_ids": [], "formation_ids": [],
            "provider": "manual", "currency": "EUR", "test_payment": True,
        }
        first = self.client.post(
            "/api/payments/checkout/", payload, format="json", HTTP_IDEMPOTENCY_KEY="checkout-course-002"
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED, first.data)
        changed = dict(payload)
        changed["currency"] = "MAD"
        second = self.client.post(
            "/api/payments/checkout/", changed, format="json", HTTP_IDEMPOTENCY_KEY="checkout-course-002"
        )
        self.assertEqual(second.status_code, status.HTTP_409_CONFLICT, second.data)
        self.assertEqual(Order.objects.filter(user=self.student).count(), 1)

    @override_settings(TEST_PAYMENTS_ENABLED=True)
    def test_refund_revokes_access_and_offsets_instructor_ledger(self):
        checkout = self.client.post(
            "/api/payments/checkout/",
            {
                "course_ids": [self.course.id], "pdf_ids": [], "formation_ids": [],
                "provider": "manual", "currency": "EUR", "test_payment": True,
            },
            format="json",
        )
        self.assertEqual(checkout.status_code, status.HTTP_201_CREATED, checkout.data)
        order_id = checkout.data["order"]["id"]
        entitlement = CourseEnrollment.objects.get(user=self.student, course=self.course)
        self.assertEqual(entitlement.source_order_id, order_id)
        self.assertEqual(
            InstructorLedgerEntry.objects.filter(instructor=self.instructor, entry_type="sale").count(), 1
        )

        admin = User.objects.create_user(
            username="refund_admin", email="refund-admin@example.com", password="passpass123", role=User.Role.ADMIN
        )
        self.client.force_authenticate(admin)
        refunded = self.client.post(
            f"/api/payments/orders/{order_id}/set_status/",
            {"status": Order.Status.REFUNDED, "reference": "manual-ref-001", "reason": "Demande client"},
            format="json",
        )
        self.assertEqual(refunded.status_code, status.HTTP_200_OK, refunded.data)
        self.assertFalse(CourseEnrollment.objects.filter(user=self.student, course=self.course).exists())
        historical = CourseEnrollment.all_objects.get(user=self.student, course=self.course)
        self.assertIsNotNone(historical.revoked_at)
        self.assertEqual(historical.source_order_id, order_id)
        amounts = list(
            InstructorLedgerEntry.objects.filter(instructor=self.instructor).order_by("entry_type").values_list("amount", flat=True)
        )
        self.assertEqual(sum(amounts, Decimal("0")), Decimal("0"))
        order = Order.objects.get(pk=order_id)
        self.assertIsNotNone(order.refunded_at)
        self.assertEqual(order.refund_reference, "manual-ref-001")

    def test_external_refund_requires_provider_reference(self):
        order = Order.objects.create(
            user=self.student, status=Order.Status.PAID, provider=Order.Provider.STRIPE,
            total_amount=Decimal("100.00"), base_total_amount=Decimal("100.00"), currency="EUR",
        )
        admin = User.objects.create_user(
            username="refund_admin_ext", email="refund-admin-ext@example.com", password="passpass123", role=User.Role.ADMIN
        )
        self.client.force_authenticate(admin)
        response = self.client.post(
            f"/api/payments/orders/{order.id}/set_status/", {"status": Order.Status.REFUNDED}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PAID)

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
            description="Test", price=Decimal("50.00"), max_students=1, published=True, status="scheduled",
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

    @override_settings(
        CINETPAY_SANDBOX_API_KEY="test_key",
        CINETPAY_SANDBOX_SITE_ID="123456",
        CINETPAY_SANDBOX_SECRET_KEY="test_secret",
    )
    @patch("apps.payments.views.create_checkout")
    def test_cinetpay_checkout_uses_xof_and_normalizes_multiple_of_five(self, create_checkout_mock):
        Currency.objects.update_or_create(
            code="XOF",
            defaults={"name": "Franc CFA BCEAO", "symbol": "F CFA", "exchange_rate": Decimal("655.957"), "decimal_places": 0, "is_active": True, "is_default": False},
        )
        PaymentGateway.objects.update_or_create(
            code="cinetpay",
            defaults={"name": "CinetPay Mobile Money", "is_active": True, "sandbox": True, "supported_currencies": ["XOF"]},
        )
        create_checkout_mock.return_value = ("https://checkout.cinetpay.test/payment/token", "LE123")
        response = self.client.post(
            "/api/payments/checkout/",
            {"course_ids": [self.course.id], "pdf_ids": [], "formation_ids": [], "provider": "cinetpay", "currency": "XOF"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        order = Order.objects.get(pk=response.data["order"]["id"])
        self.assertEqual(order.provider, Order.Provider.CINETPAY)
        self.assertEqual(order.currency, "XOF")
        self.assertEqual(order.total_amount % Decimal("5"), Decimal("0"))
        self.assertEqual(order.total_amount, Decimal("65595"))

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

    def test_admin_can_remove_and_readd_unused_supported_gateway(self):
        # Les drivers supportés sont précréés par migration. L'admin peut supprimer
        # un driver inutilisé puis le recréer, mais ne doit jamais créer un doublon.
        existing = PaymentGateway.objects.get(code="youcanpay")
        deleted = self.client.delete(f"/api/payments/admin/gateways/{existing.id}/")
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)
        created = self.client.post(
            "/api/payments/admin/gateways/",
            {"code": "youcanpay", "name": "YouCan Pay", "description": "Maroc", "is_active": False, "sandbox": True, "supported_currencies": ["MAD"], "sort_order": 10},
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)

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

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", DEFAULT_FROM_EMAIL="KalanPro <no-reply@example.com>")
    def test_admin_can_test_email_configuration(self):
        response = self.client.post("/api/payments/admin/test-email/", {"email": "diagnostic@example.com"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["diagnostic@example.com"])

    @patch("apps.payments.views.test_provider")
    def test_admin_can_run_gateway_diagnostic(self, test_provider_mock):
        gateway = PaymentGateway.objects.get(code="youcanpay")
        gateway.is_active = False
        gateway.sandbox = True
        gateway.supported_currencies = ["MAD"]
        gateway.save(update_fields=["is_active", "sandbox", "supported_currencies"])
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
        Currency.objects.update_or_create(
            code="XOF", defaults={"name": "Franc CFA", "symbol": "F CFA", "exchange_rate": Decimal("65"),
            "decimal_places": 0, "is_active": True, "is_default": False},
        )
        self.assertEqual(_to_minor_units(Decimal("15000"), "XOF"), 15000)
        self.assertEqual(_from_minor_units(15000, "XOF"), Decimal("15000"))
        self.assertEqual(_to_minor_units(Decimal("123.45"), "MAD"), 12345)
        self.assertEqual(_from_minor_units(12345, "MAD"), Decimal("123.45"))
        self.assertEqual(normalize_provider_amount("cinetpay", Decimal("15002"), "XOF"), Decimal("15000"))
        self.assertEqual(normalize_provider_amount("cinetpay", Decimal("15003"), "XOF"), Decimal("15005"))



class MentorshipPaymentRegressionTests(APITestCase):
    def setUp(self):
        from apps.formations.models import MentorshipOffering
        from apps.formations.mentorship import create_slot, reserve_booking
        from django.utils import timezone
        from datetime import timedelta

        self.mentor = User.objects.create_user(
            username="pay_mentor", email="pay-mentor@example.com", password="passpass123", role=User.Role.INSTRUCTOR
        )
        self.student = User.objects.create_user(
            username="pay_mentee", email="pay-mentee@example.com", password="passpass123", role=User.Role.STUDENT
        )
        Currency.objects.update_or_create(
            code="EUR",
            defaults={"name": "Euro", "symbol": "€", "exchange_rate": Decimal("1"), "decimal_places": 2, "is_active": True, "is_default": True},
        )
        PaymentGateway.objects.update_or_create(
            code="stripe",
            defaults={"name": "Stripe", "is_active": True, "supported_currencies": ["EUR"], "sandbox": True},
        )
        self.offer = MentorshipOffering.objects.create(
            instructor=self.mentor,
            title="Mentorat paiement",
            description="Test du cycle paiement mentorat",
            price=Decimal("20.00"),
            published=True,
            booking_notice_hours=1,
        )
        self.slot = create_slot(self.offer, timezone.now() + timedelta(days=2))
        self.booking = reserve_booking(user=self.student, slot=self.slot, learner_note="Objectif paiement")
        self.client.force_authenticate(self.student)

    @override_settings(TEST_PAYMENTS_ENABLED=True)
    def test_internal_test_payment_confirms_mentorship_and_revenue_split(self):
        from apps.formations.models import MentorshipBooking, FormationSessionInvite

        response = self.client.post(
            "/api/payments/checkout/",
            {
                "course_ids": [], "pdf_ids": [], "formation_ids": [],
                "mentorship_booking_ids": [self.booking.id],
                "provider": "stripe", "currency": "EUR", "test_payment": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, MentorshipBooking.Status.CONFIRMED)
        self.assertIsNone(self.booking.expires_at)
        self.assertTrue(FormationSessionInvite.objects.filter(
            session=self.slot.session, email__iexact=self.student.email, revoked_at__isnull=True
        ).exists())
        item = OrderItem.objects.get(order_id=response.data["order"]["id"], mentorship_booking=self.booking)
        self.assertEqual(item.item_type, OrderItem.ItemType.MENTORING)
        self.assertEqual(item.platform_fee_amount, Decimal("3.00"))
        self.assertEqual(item.instructor_earning_amount, Decimal("17.00"))

    @override_settings(TEST_PAYMENTS_ENABLED=True)
    def test_mentorship_uses_dedicated_configurable_commission(self):
        from apps.accounts.models import PlatformSettings

        config = PlatformSettings.load()
        config.mentor_commission_percent = 10
        config.save()
        response = self.client.post(
            "/api/payments/checkout/",
            {
                "course_ids": [], "pdf_ids": [], "formation_ids": [],
                "mentorship_booking_ids": [self.booking.id],
                "provider": "stripe", "currency": "EUR", "test_payment": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        item = OrderItem.objects.get(order_id=response.data["order"]["id"], mentorship_booking=self.booking)
        self.assertEqual(item.platform_fee_amount, Decimal("2.00"))
        self.assertEqual(item.instructor_earning_amount, Decimal("18.00"))

    @override_settings(STRIPE_SECRET_KEY="sk_test_fake")
    @patch("apps.payments.views.create_checkout")
    def test_external_checkout_extends_slot_hold_to_two_hours(self, create_checkout_mock):
        from django.utils import timezone
        from datetime import timedelta

        create_checkout_mock.return_value = ("https://checkout.stripe.test/mentor", "cs_mentor_1")
        before = timezone.now()
        response = self.client.post(
            "/api/payments/checkout/",
            {
                "course_ids": [], "pdf_ids": [], "formation_ids": [],
                "mentorship_booking_ids": [self.booking.id],
                "provider": "stripe", "currency": "EUR",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.booking.refresh_from_db()
        self.assertGreaterEqual(self.booking.expires_at, before + timedelta(minutes=119))
        self.assertEqual(Order.objects.get(pk=response.data["order"]["id"]).status, Order.Status.PENDING)

    @override_settings(STRIPE_SECRET_KEY="sk_test_fake")
    @patch("apps.payments.views.verify_payment")
    @patch("apps.payments.views.create_checkout")
    def test_failed_external_payment_releases_mentorship_slot(self, create_checkout_mock, verify_payment_mock):
        from apps.formations.models import MentorshipBooking
        from django.utils import timezone
        from datetime import timedelta

        create_checkout_mock.return_value = ("https://checkout.stripe.test/mentor-failed", "cs_mentor_failed")
        checkout = self.client.post(
            "/api/payments/checkout/",
            {
                "course_ids": [], "pdf_ids": [], "formation_ids": [],
                "mentorship_booking_ids": [self.booking.id],
                "provider": "stripe", "currency": "EUR",
            },
            format="json",
        )
        self.assertEqual(checkout.status_code, status.HTTP_201_CREATED, checkout.data)
        order = Order.objects.get(pk=checkout.data["order"]["id"])

        # Même si l'expiration locale passe, une commande prestataire encore PENDING
        # doit continuer de verrouiller le créneau jusqu'à un état terminal.
        self.booking.expires_at = timezone.now() - timedelta(minutes=1)
        self.booking.save(update_fields=["expires_at", "updated_at"])
        from apps.formations.mentorship import expire_stale_bookings
        expire_stale_bookings(self.slot)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, MentorshipBooking.Status.PENDING_PAYMENT)

        cancel = self.client.post(f"/api/mentorship/bookings/{self.booking.id}/cancel/", {}, format="json")
        self.assertEqual(cancel.status_code, status.HTTP_409_CONFLICT, cancel.data)

        verify_payment_mock.return_value = {
            "paid": False, "amount": Decimal("20.00"), "currency": "EUR", "status": "FAILED"
        }
        confirm = self.client.post(f"/api/payments/orders/{order.id}/confirm/", {}, format="json")
        self.assertEqual(confirm.status_code, status.HTTP_402_PAYMENT_REQUIRED, confirm.data)
        order.refresh_from_db()
        self.booking.refresh_from_db()
        self.assertEqual(order.status, Order.Status.FAILED)
        self.assertEqual(self.booking.status, MentorshipBooking.Status.EXPIRED)
        self.assertIsNone(self.booking.expires_at)

    def test_mobile_money_payout_requires_e164_number(self):
        self.client.force_authenticate(self.mentor)
        invalid = self.client.patch(
            "/api/payments/instructor/payout-profile/",
            {"method": "mobile_money", "account_name": "Mentor", "account_reference": "771234567"},
            format="json",
        )
        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST, invalid.data)
        self.assertIn("account_reference", invalid.data)

        unknown_dial = self.client.patch(
            "/api/payments/instructor/payout-profile/",
            {"method": "mobile_money", "account_name": "Mentor", "account_reference": "+99912345678"},
            format="json",
        )
        self.assertEqual(unknown_dial.status_code, status.HTTP_400_BAD_REQUEST, unknown_dial.data)
        self.assertIn("account_reference", unknown_dial.data)

        valid = self.client.patch(
            "/api/payments/instructor/payout-profile/",
            {"method": "mobile_money", "account_name": "Mentor", "account_reference": "+221771234567"},
            format="json",
        )
        self.assertEqual(valid.status_code, status.HTTP_200_OK, valid.data)
        self.assertEqual(valid.data["account_reference"], "+221771234567")


class PaymentOperationalAuditTests(APITestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username="audit_seller", email="audit-seller@example.com", password="passpass123", role=User.Role.INSTRUCTOR
        )
        self.student = User.objects.create_user(
            username="audit_buyer", email="audit-buyer@example.com", password="passpass123", role=User.Role.STUDENT
        )
        self.admin = User.objects.create_user(
            username="audit_admin", email="audit-admin@example.com", password="passpass123", role=User.Role.ADMIN
        )
        category = Category.objects.create(name="Audit finance")
        self.course = Course.objects.create(
            instructor=self.instructor, category=category, title="Cours audit paiement",
            description="Test audit", price=Decimal("100.00"), published=True,
        )
        Currency.objects.update_or_create(
            code="EUR",
            defaults={"name": "Euro", "symbol": "€", "exchange_rate": Decimal("1"), "decimal_places": 2, "is_active": True, "is_default": True},
        )
        PaymentGateway.objects.update_or_create(
            code="stripe",
            defaults={"name": "Stripe", "is_active": True, "supported_currencies": ["EUR"], "sandbox": True},
        )
        self.client.force_authenticate(self.student)

    @override_settings(STRIPE_SECRET_KEY="sk_test_fake")
    @patch("apps.payments.views.create_checkout")
    def test_checkout_creates_attempt_expiry_and_audit_event(self, create_checkout_mock):
        create_checkout_mock.return_value = ("https://checkout.stripe.test/audit", "cs_audit_001")
        response = self.client.post(
            "/api/payments/checkout/",
            {"course_ids": [self.course.id], "pdf_ids": [], "formation_ids": [], "provider": "stripe", "currency": "EUR"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        order = Order.objects.get(pk=response.data["order"]["id"])
        self.assertIsNotNone(order.expires_at)
        self.assertEqual(order.provider_status, "REDIRECTED")
        attempt = PaymentAttempt.objects.get(order=order)
        self.assertEqual(attempt.status, PaymentAttempt.Status.REDIRECTED)
        self.assertEqual(attempt.provider_reference, "cs_audit_001")
        self.assertTrue(PaymentEvent.objects.filter(order=order, event_type="checkout.created").exists())
        self.assertTrue(PaymentEvent.objects.filter(order=order, event_type="checkout.redirect_created").exists())

    @override_settings(STRIPE_SECRET_KEY="sk_test_fake")
    @patch("apps.payments.views.verify_payment")
    @patch("apps.payments.views.create_checkout")
    def test_financial_mismatch_opens_issue_and_never_fulfills(self, create_checkout_mock, verify_payment_mock):
        create_checkout_mock.return_value = ("https://checkout.stripe.test/mismatch", "cs_mismatch_001")
        verify_payment_mock.return_value = {
            "paid": True, "amount": Decimal("1.00"), "currency": "EUR", "status": "PAID", "payment_method": "card"
        }
        checkout = self.client.post(
            "/api/payments/checkout/",
            {"course_ids": [self.course.id], "pdf_ids": [], "formation_ids": [], "provider": "stripe", "currency": "EUR"},
            format="json",
        )
        order_id = checkout.data["order"]["id"]
        confirm = self.client.post(f"/api/payments/orders/{order_id}/confirm/", {}, format="json")
        self.assertEqual(confirm.status_code, status.HTTP_409_CONFLICT, confirm.data)
        order = Order.objects.get(pk=order_id)
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertFalse(CourseEnrollment.objects.filter(user=self.student, course=self.course).exists())
        self.assertTrue(PaymentIssue.objects.filter(
            order=order, issue_type=PaymentIssue.IssueType.AMOUNT_MISMATCH, status=PaymentIssue.Status.OPEN
        ).exists())
        self.assertNotEqual(
            order.payment_attempts.latest("started_at").status, PaymentAttempt.Status.PAID
        )

    def test_payment_event_redacts_sensitive_payload_and_persistent_duplicate(self):
        from .lifecycle import record_event
        order = Order.objects.create(
            user=self.student, provider=Order.Provider.CINETPAY, provider_reference="REF-001",
            total_amount=Decimal("100.00"), base_total_amount=Decimal("100.00"), currency="EUR",
        )
        first, created = record_event(
            order=order, provider=Order.Provider.CINETPAY, source=PaymentEvent.Source.WEBHOOK,
            event_type="audit.test", external_id="evt-audit-001",
            payload={"amount": "100", "customer_email": "secret@example.com", "cel_phone_num": "+221771234567"},
        )
        second, created_again = record_event(
            order=order, provider=Order.Provider.CINETPAY, source=PaymentEvent.Source.WEBHOOK,
            event_type="audit.test", external_id="evt-audit-001",
            payload={"amount": "100"},
        )
        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(first.payload["customer_email"], "[redacted]")
        self.assertEqual(first.payload["cel_phone_num"], "[redacted]")
        self.assertEqual(first.payload["amount"], "100")

    def test_stale_pending_task_opens_issue_without_forcing_failure(self):
        from django.utils import timezone
        from datetime import timedelta
        from .tasks import flag_stale_pending_payments
        order = Order.objects.create(
            user=self.student, provider=Order.Provider.CINETPAY, provider_reference="STALE-001",
            status=Order.Status.PENDING, total_amount=Decimal("100.00"), base_total_amount=Decimal("100.00"),
            currency="EUR", expires_at=timezone.now() - timedelta(hours=1),
        )
        result = flag_stale_pending_payments()
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(result["issues_created"], 1)
        self.assertTrue(PaymentIssue.objects.filter(
            order=order, issue_type=PaymentIssue.IssueType.STALE_PENDING, status=PaymentIssue.Status.OPEN
        ).exists())

    def test_payment_audit_endpoint_is_admin_only(self):
        order = Order.objects.create(
            user=self.student, provider=Order.Provider.MANUAL, status=Order.Status.PENDING,
            total_amount=Decimal("100.00"), base_total_amount=Decimal("100.00"), currency="EUR",
        )
        student_response = self.client.get(f"/api/payments/orders/{order.id}/payment-audit/")
        self.assertEqual(student_response.status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(self.admin)
        admin_response = self.client.get(f"/api/payments/orders/{order.id}/payment-audit/")
        self.assertEqual(admin_response.status_code, status.HTTP_200_OK, admin_response.data)
        self.assertIn("attempts", admin_response.data)
        self.assertIn("events", admin_response.data)
        self.assertIn("issues", admin_response.data)
