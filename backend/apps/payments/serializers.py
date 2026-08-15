from rest_framework import serializers
from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ["id", "item_type", "course", "pdf_product", "unit_price", "title"]

    def get_title(self, obj):
        return obj.course.title if obj.course else (obj.pdf_product.title if obj.pdf_product else "")


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "status", "provider", "total_amount", "invoice_number",
            "created_at", "paid_at", "items",
        ]


class CheckoutSerializer(serializers.Serializer):
    """Payload attendu pour créer une commande à partir du panier front-end."""
    course_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    pdf_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    provider = serializers.ChoiceField(choices=Order.Provider.choices, default=Order.Provider.STRIPE)
