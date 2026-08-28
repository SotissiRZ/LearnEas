from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.catalog.models import Category, Course
from apps.enrollments.models import CourseEnrollment
from .models import Order, OrderItem


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

    def test_confirmed_purchase_creates_access_and_finance_snapshot(self):
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

