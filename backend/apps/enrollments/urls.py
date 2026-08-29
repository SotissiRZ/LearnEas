from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import CourseEnrollmentViewSet, WishlistViewSet, MyPDFsViewSet, CertificateViewSet, CertificateVerifyView

router = DefaultRouter()
router.register("my-courses", CourseEnrollmentViewSet, basename="my-courses")
router.register("wishlist", WishlistViewSet, basename="wishlist")
router.register("my-pdfs", MyPDFsViewSet, basename="my-pdfs")
router.register("certificates", CertificateViewSet, basename="certificates")

urlpatterns = [
    path("certificates/verify/<uuid:code>/", CertificateVerifyView.as_view(), name="certificate-verify"),
] + router.urls
