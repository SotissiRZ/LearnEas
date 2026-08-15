from rest_framework.routers import DefaultRouter
from .views import CourseEnrollmentViewSet, WishlistViewSet, MyPDFsViewSet

router = DefaultRouter()
router.register("my-courses", CourseEnrollmentViewSet, basename="my-courses")
router.register("wishlist", WishlistViewSet, basename="wishlist")
router.register("my-pdfs", MyPDFsViewSet, basename="my-pdfs")

urlpatterns = router.urls
