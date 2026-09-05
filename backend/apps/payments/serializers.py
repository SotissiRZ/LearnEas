from rest_framework import serializers
from apps.common.phone import normalize_e164_phone
from .models import (
    Order, OrderItem, PayoutProfile, InstructorPayout, Currency, PaymentGateway,
    PaymentAttempt, PaymentEvent, PaymentIssue,
)


class OrderItemSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    instructor_name = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            "id", "item_type", "course", "pdf_product", "formation", "mentorship_booking", "entitlement_code", "unit_price", "title",
            "instructor", "instructor_name", "platform_fee_amount", "instructor_earning_amount",
        ]

    def get_title(self, obj):
        if obj.course:
            return obj.course.title
        if obj.pdf_product:
            return obj.pdf_product.title
        if obj.formation:
            return obj.formation.title
        if obj.mentorship_booking:
            return f"Mentorat · {obj.mentorship_booking.offering.title}"
        employer_titles = {
            "single_post": "Annonce recruteur · 30 jours",
            "pro": "KalanPro Pro recrutement · 30 jours",
            "business": "KalanPro Business · 30 jours",
        }
        if obj.item_type == OrderItem.ItemType.EMPLOYER:
            return employer_titles.get(obj.entitlement_code, "Droit recruteur KalanPro")
        return ""

    def get_instructor_name(self, obj):
        if not obj.instructor:
            return ""
        return obj.instructor.get_full_name() or obj.instructor.username


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    customer_name = serializers.SerializerMethodField()
    customer_email = serializers.EmailField(source="user.email", read_only=True)
    open_payment_issue_count = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id", "status", "provider", "provider_sandbox", "provider_status", "payment_method",
            "last_provider_check_at", "expires_at", "base_total_amount", "total_amount", "currency", "invoice_number",
            "created_at", "paid_at", "refunded_at", "refund_reference", "refund_reason",
            "items", "customer_name", "customer_email", "open_payment_issue_count",
        ]

    def get_customer_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def get_open_payment_issue_count(self, obj):
        annotated = getattr(obj, "open_payment_issue_count", None)
        if annotated is not None:
            return int(annotated)
        return obj.payment_issues.filter(status=PaymentIssue.Status.OPEN).count()


class PaymentAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentAttempt
        fields = [
            "id", "attempt_number", "provider", "provider_sandbox", "provider_reference", "status",
            "amount", "currency", "provider_status", "payment_method", "check_count", "error_count",
            "last_error", "last_checked_at", "started_at", "updated_at", "completed_at",
        ]
        read_only_fields = fields


class PaymentEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentEvent
        fields = [
            "id", "provider", "provider_sandbox", "source", "event_type", "external_id", "outcome",
            "payload_hash", "payload", "request_id", "message", "created_at",
        ]
        read_only_fields = fields


class PaymentIssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentIssue
        fields = [
            "id", "issue_type", "severity", "status", "message", "expected", "observed",
            "created_at", "resolved_at", "resolution_note",
        ]
        read_only_fields = fields


class CheckoutSerializer(serializers.Serializer):
    course_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False, default=list)
    pdf_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False, default=list)
    formation_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False, default=list)
    mentorship_booking_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False, default=list)
    employer_product = serializers.ChoiceField(
        choices=["single_post", "pro", "business"], required=False, allow_blank=True, default=""
    )
    provider = serializers.CharField(max_length=30, default=Order.Provider.STRIPE)
    currency = serializers.CharField(max_length=3, default="EUR")
    test_payment = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        attrs["provider"] = attrs["provider"].strip().lower()
        attrs["currency"] = attrs["currency"].strip().upper()
        for field in ("course_ids", "pdf_ids", "formation_ids", "mentorship_booking_ids"):
            attrs[field] = list(dict.fromkeys(attrs[field]))
        if attrs.get("employer_product") and any(
            attrs[field] for field in ("course_ids", "pdf_ids", "formation_ids", "mentorship_booking_ids")
        ):
            raise serializers.ValidationError(
                {"employer_product": "Un droit recruteur doit être acheté dans une commande dédiée."}
            )
        return attrs


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ["id", "code", "name", "symbol", "exchange_rate", "decimal_places", "is_active", "is_default", "sort_order"]

    def validate_code(self, value):
        value = value.strip().upper()
        if len(value) != 3 or not value.isalpha():
            raise serializers.ValidationError("Utilisez un code ISO-4217 à 3 lettres.")
        return value

    def validate_exchange_rate(self, value):
        if value <= 0:
            raise serializers.ValidationError("Le taux doit être strictement positif.")
        return value

    def validate_decimal_places(self, value):
        if value > 2:
            raise serializers.ValidationError("Le nombre de décimales doit être compris entre 0 et 2 pour les commandes KalanPro.")
        return value

    def validate(self, attrs):
        if self.instance and "code" in attrs and attrs["code"] != self.instance.code:
            raise serializers.ValidationError({"code": "Le code d'une devise existante ne peut pas être modifié. Créez une nouvelle devise."})
        code = attrs.get("code", getattr(self.instance, "code", ""))
        if code == "EUR":
            if "is_active" in attrs and not attrs["is_active"]:
                raise serializers.ValidationError({"is_active": "EUR est la devise comptable de base et doit rester active."})
            if "exchange_rate" in attrs and attrs["exchange_rate"] != 1:
                raise serializers.ValidationError({"exchange_rate": "Le taux de la devise comptable EUR doit rester égal à 1."})
            attrs["is_active"] = True
            attrs["exchange_rate"] = 1
        return attrs


class PaymentGatewaySerializer(serializers.ModelSerializer):
    configured = serializers.SerializerMethodField()

    class Meta:
        model = PaymentGateway
        fields = ["id", "code", "name", "description", "is_active", "sandbox", "supported_currencies", "sort_order", "configured"]
        read_only_fields = ["configured"]

    def get_configured(self, obj):
        from .providers import is_configured
        return is_configured(obj.code, sandbox=obj.sandbox)

    def validate_code(self, value):
        value = value.strip().lower()
        allowed = {"stripe", "youcanpay", "geniuspay", "cinetpay", "manual"}
        if value not in allowed:
            raise serializers.ValidationError("Driver inconnu. Drivers disponibles : stripe, youcanpay, geniuspay, cinetpay, manual.")
        return value

    def validate_supported_currencies(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Une liste de codes devises est attendue.")
        codes = sorted({str(code).strip().upper() for code in value if str(code).strip()})
        invalid = [code for code in codes if len(code) != 3 or not code.isalpha()]
        if invalid:
            raise serializers.ValidationError(f"Codes de devise invalides : {', '.join(invalid)}")
        from .models import Currency
        missing = [code for code in codes if not Currency.objects.filter(code=code).exists()]
        if missing:
            raise serializers.ValidationError(f"Ajoutez d'abord les devises suivantes : {', '.join(missing)}")
        return codes

    def validate(self, attrs):
        if self.instance and "code" in attrs and attrs["code"] != self.instance.code:
            raise serializers.ValidationError({"code": "Le driver d'un moyen de paiement existant ne peut pas être modifié."})
        return attrs


class PayoutProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayoutProfile
        fields = ["method", "account_name", "account_reference", "updated_at"]
        read_only_fields = ["updated_at"]

    def validate(self, attrs):
        method = attrs.get("method", getattr(self.instance, "method", PayoutProfile.Method.BANK) if self.instance else PayoutProfile.Method.BANK)
        reference = str(attrs.get("account_reference", getattr(self.instance, "account_reference", "") if self.instance else "") or "").strip()
        if method == PayoutProfile.Method.MOBILE_MONEY:
            try:
                attrs["account_reference"] = normalize_e164_phone(reference, required=True)
            except ValueError as exc:
                raise serializers.ValidationError({"account_reference": str(exc)})
        elif method == PayoutProfile.Method.PAYPAL and reference:
            try:
                serializers.EmailField().run_validation(reference)
            except serializers.ValidationError:
                raise serializers.ValidationError({"account_reference": "Adresse email PayPal invalide."})
            attrs["account_reference"] = reference.lower()
        else:
            attrs["account_reference"] = reference
        attrs["account_name"] = str(attrs.get("account_name", getattr(self.instance, "account_name", "") if self.instance else "") or "").strip()
        return attrs


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
