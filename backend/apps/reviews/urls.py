from rest_framework.routers import DefaultRouter
from .views import ReviewViewSet, LessonCommentViewSet

router = DefaultRouter()
router.register("reviews", ReviewViewSet, basename="review")
router.register("comments", LessonCommentViewSet, basename="lesson-comment")

urlpatterns = router.urls
