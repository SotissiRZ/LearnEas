from django.contrib import admin
from .models import Domain, Category, Course, Section, Lesson, PDFResource, PDFProduct


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "order", "icon")
    list_editable = ("order",)
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1


class SectionInline(admin.TabularInline):
    model = Section
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "domain", "slug", "icon")
    list_filter = ("domain",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "instructor", "category", "price", "published", "featured",
                     "total_lessons", "total_duration_minutes", "students_count", "rating_avg",
                     "video_completion_threshold_percent")
    list_filter = ("published", "featured", "level", "category")
    search_fields = ("title", "description")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("course", "title", "order")
    inlines = [LessonInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("section", "title", "duration_minutes", "streaming_status", "is_preview", "offline_download_allowed", "order")
    list_filter = ("streaming_status", "is_preview", "offline_download_allowed")


@admin.register(PDFResource)
class PDFResourceAdmin(admin.ModelAdmin):
    list_display = ("course", "title", "page_count", "is_free_sample")


@admin.register(PDFProduct)
class PDFProductAdmin(admin.ModelAdmin):
    list_display = ("title", "instructor", "category", "price", "published", "featured", "downloads_count")
    list_filter = ("published", "featured", "level", "category")
    search_fields = ("title", "description")
    prepopulated_fields = {"slug": ("title",)}
