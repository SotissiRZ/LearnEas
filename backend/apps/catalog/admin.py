from django.contrib import admin
from .models import Category, Course, Section, Lesson, PDFResource, PDFProduct


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1


class SectionInline(admin.TabularInline):
    model = Section
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "icon")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "instructor", "category", "price", "published", "featured",
                     "total_lessons", "total_duration_minutes", "students_count", "rating_avg")
    list_filter = ("published", "featured", "level", "category")
    search_fields = ("title", "description")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("course", "title", "order")
    inlines = [LessonInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("section", "title", "duration_minutes", "streaming_status", "is_preview", "order")
    list_filter = ("streaming_status", "is_preview")


@admin.register(PDFResource)
class PDFResourceAdmin(admin.ModelAdmin):
    list_display = ("course", "title", "page_count", "is_free_sample")


@admin.register(PDFProduct)
class PDFProductAdmin(admin.ModelAdmin):
    list_display = ("title", "instructor", "category", "price", "published", "featured", "downloads_count")
    list_filter = ("published", "featured", "level", "category")
    search_fields = ("title", "description")
    prepopulated_fields = {"slug": ("title",)}
