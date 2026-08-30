from decimal import Decimal
from unittest.mock import patch

from django.test import override_settings

from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.catalog.models import Category, Course
from apps.enrollments.models import CourseEnrollment
from apps.formations.models import InteractiveFormation
from .models import Order, OrderItem, FormationSeatReservation


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

    @override_settings(STRIPE_SECRET_KEY="sk_test_fake")
    @patch("apps.payments.views.stripe.checkout.Session.create")
    def test_confirmed_purchase_creates_access_and_finance_snapshot(self, stripe_create):
        stripe_create.return_value.id = "cs_test_123"
        stripe_create.return_value.url = "https://checkout.stripe.test/session"
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
    @patch("apps.payments.views.stripe.checkout.Session.create")
    def test_paid_live_checkout_reserves_last_seat(self, stripe_create):
        stripe_create.return_value.id = "cs_live_1"
        stripe_create.return_value.url = "https://checkout.stripe.test/live"
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
