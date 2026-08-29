from django.contrib import admin
from .models import CourseEnrollment, LessonProgress, PDFPurchase, Wishlist

admin.site.register(CourseEnrollment)
admin.site.register(LessonProgress)
admin.site.register(PDFPurchase)
admin.site.register(Wishlist)


from .models import Certificate
admin.site.register(Certificate)
