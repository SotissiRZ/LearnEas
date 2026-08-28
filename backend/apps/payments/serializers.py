from rest_framework import serializers
from .models import Order, OrderItem, PayoutProfile, InstructorPayout


class OrderItemSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    instructor_name = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            "id", "item_type", "course", "pdf_product", "formation", "unit_price", "title",
            "instructor", "instructor_name", "platform_fee_amount", "instructor_earning_amount",
        ]

    def get_title(self, obj):
        if obj.course:
            return obj.course.title
        if obj.pdf_product:
            return obj.pdf_product.title
        if obj.formation:
            return obj.formation.title
        return ""

    def get_instructor_name(self, obj):
        if not obj.instructor:
            return ""
        return obj.instructor.get_full_name() or obj.instructor.username


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    customer_name = serializers.SerializerMethodField()
    customer_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "status", "provider", "total_amount", "invoice_number",
            "created_at", "paid_at", "items", "customer_name", "customer_email",
        ]

    def get_customer_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


class CheckoutSerializer(serializers.Serializer):
    course_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    pdf_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    formation_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    provider = serializers.ChoiceField(choices=Order.Provider.choices, default=Order.Provider.STRIPE)


class PayoutProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayoutProfile
        fields = ["method", "account_name", "account_reference", "updated_at"]
        read_only_fields = ["updated_at"]


class InstructorPayoutSerializer(serializers.ModelSerializer):
    instructor_name = serializers.SerializerMethodField()
    instructor_email = serializers.EmailField(source="instructor.email", read_only=True)

    class Meta:
        model = InstructorPayout
        fields = [
            "id", "instructor", "instructor_name", "instructor_email", "amount", "status",
            "method", "account_reference_snapshot", "requested_at", "processed_at", "reference", "note",
        ]
        read_only_fields = [
            "id", "instructor", "status", "method", "account_reference_snapshot",
            "requested_at", "processed_at", "reference", "note",
        ]

    def get_instructor_name(self, obj):
        return obj.instructor.get_full_name() or obj.instructor.username
