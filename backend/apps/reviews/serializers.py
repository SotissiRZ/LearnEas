from rest_framework import serializers
from apps.accounts.serializers import UserPublicSerializer
from .models import Review, LessonComment


class ReviewSerializer(serializers.ModelSerializer):
    user = UserPublicSerializer(read_only=True)

    class Meta:
        model = Review
        fields = ["id", "user", "course", "pdf_product", "rating", "comment", "created_at"]
        read_only_fields = ["user"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        review = super().create(validated_data)
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
