from rest_framework import serializers
from django.db.models import Avg, Count
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

    def validate(self, attrs):
        course = attrs.get("course", getattr(self.instance, "course", None))
        pdf = attrs.get("pdf_product", getattr(self.instance, "pdf_product", None))
        if bool(course) == bool(pdf):
            raise serializers.ValidationError("Un avis doit cibler exactement un cours ou un PDF.")
        comment = str(attrs.get("comment", getattr(self.instance, "comment", "")) or "").strip()
        if len(comment) > 5000:
            raise serializers.ValidationError({"comment": "Le commentaire est limité à 5 000 caractères."})
        attrs["comment"] = comment
        return attrs

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
        stats = qs.aggregate(avg=Avg("rating"), count=Count("id"))
        target.rating_avg = round(stats["avg"] or 0, 2)
        target.rating_count = stats["count"] or 0
        target.save(update_fields=["rating_avg", "rating_count"])


class LessonCommentSerializer(serializers.ModelSerializer):
    user = UserPublicSerializer(read_only=True)
    replies = serializers.SerializerMethodField()
    lesson_title = serializers.CharField(source="lesson.title", read_only=True)
    course_title = serializers.CharField(source="lesson.section.course.title", read_only=True)

    class Meta:
        model = LessonComment
        fields = ["id", "user", "lesson", "lesson_title", "course_title", "parent", "content", "created_at", "replies"]
        read_only_fields = ["user"]

    def get_replies(self, obj):
        if obj.parent_id is not None:
            return []
        return LessonCommentSerializer(obj.replies.all(), many=True).data

    def validate(self, attrs):
        lesson = attrs.get("lesson", getattr(self.instance, "lesson", None))
        parent = attrs.get("parent", getattr(self.instance, "parent", None))
        content = str(attrs.get("content", getattr(self.instance, "content", "")) or "").strip()
        if not content:
            raise serializers.ValidationError({"content": "Le commentaire ne peut pas être vide."})
        if len(content) > 5000:
            raise serializers.ValidationError({"content": "Le commentaire est limité à 5 000 caractères."})
        if parent:
            if parent.parent_id is not None:
                raise serializers.ValidationError({"parent": "Une réponse ne peut pas être imbriquée au-delà d'un niveau."})
            if lesson and parent.lesson_id != lesson.id:
                raise serializers.ValidationError({"parent": "La réponse doit appartenir à la même leçon."})
        attrs["content"] = content
        return attrs

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)
