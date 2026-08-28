from rest_framework import serializers
from apps.accounts.serializers import UserPublicSerializer
from .models import Review, LessonComment


class ReviewSerializer(serializers.ModelSerializer):
    user = UserPublicSerializer(read_only=True)
    target_title = serializers.SerializerMethodField()
    target_type = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ["id", "user", "course", "pdf_product", "target_title", "target_type", "rating", "comment", "created_at"]
        read_only_fields = ["user"]

    def get_target_title(self, obj):
        target = obj.course or obj.pdf_product
        return target.title if target else ""

    def get_target_type(self, obj):
        return "course" if obj.course_id else "pdf" if obj.pdf_product_id else ""

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        review = super().create(validated_data)
        self._refresh_target_rating(review)
        return review

    def update(self, instance, validated_data):
        review = super().update(instance, validated_data)
        self._refresh_target_rating(review)
        return review

    def _refresh_target_rating(self, review):
        target = review.course or review.pdf_product
        if not target:
            return
        qs = Review.objects.filter(course=review.course) if review.course else Review.objects.filter(pdf_product=review.pdf_product)
        count = qs.count()
        avg = sum(r.rating for r in qs) / count if count else 0
        target.rating_avg = round(avg, 2)
        target.rating_count = count
        target.save(update_fields=["rating_avg", "rating_count"])


class LessonCommentSerializer(serializers.ModelSerializer):
    user = UserPublicSerializer(read_only=True)
    replies = serializers.SerializerMethodField()

    class Meta:
        model = LessonComment
        fields = ["id", "user", "lesson", "parent", "content", "created_at", "replies"]
        read_only_fields = ["user"]

    def get_replies(self, obj):
        if obj.parent_id is not None:
            return []
        return LessonCommentSerializer(obj.replies.all(), many=True).data

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)
