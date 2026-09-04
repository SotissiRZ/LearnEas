from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    CourseEnrollmentViewSet, LessonNoteViewSet, WishlistViewSet, MyPDFsViewSet, CertificateViewSet,
    CertificateVerifyView, CertificateLookupView, CertificateQRView,
)

router = DefaultRouter()
router.register("my-courses", CourseEnrollmentViewSet, basename="my-courses")
router.register("lesson-notes", LessonNoteViewSet, basename="lesson-notes")
router.register("wishlist", WishlistViewSet, basename="wishlist")
router.register("my-pdfs", MyPDFsViewSet, basename="my-pdfs")
router.register("certificates", CertificateViewSet, basename="certificates")

urlpatterns = [
    path("certificates/lookup/", CertificateLookupView.as_view(), name="certificate-lookup"),
    path("certificates/verify/<uuid:code>/qr/", CertificateQRView.as_view(), name="certificate-qr"),
    path("certificates/verify/<uuid:code>/", CertificateVerifyView.as_view(), name="certificate-verify"),
] + router.urls
