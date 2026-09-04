from rest_framework.routers import DefaultRouter
from .views import (
    DomainViewSet, CategoryViewSet, CourseViewSet, SectionViewSet, LessonViewSet,
    PDFResourceViewSet, PDFProductViewSet,
)

router = DefaultRouter()
router.register("domains", DomainViewSet, basename="domain")
router.register("categories", CategoryViewSet, basename="category")
router.register("courses", CourseViewSet, basename="course")
router.register("sections", SectionViewSet, basename="section")
router.register("lessons", LessonViewSet, basename="lesson")
router.register("pdf-resources", PDFResourceViewSet, basename="pdf-resource")
router.register("pdfs", PDFProductViewSet, basename="pdf-product")

urlpatterns = router.urls
