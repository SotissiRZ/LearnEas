from django.db import migrations, models


def clean_wishlist(apps, schema_editor):
    Wishlist = apps.get_model("enrollments", "Wishlist")
    Wishlist.objects.filter(course__isnull=True, pdf_product__isnull=True).delete()
    Wishlist.objects.filter(course__isnull=False, pdf_product__isnull=False).update(pdf_product=None)
    seen_course = set()
    for item in Wishlist.objects.filter(course__isnull=False).order_by("id"):
        key = (item.user_id, item.course_id)
        if key in seen_course:
            item.delete()
        else:
            seen_course.add(key)
    seen_pdf = set()
    for item in Wishlist.objects.filter(pdf_product__isnull=False).order_by("id"):
        key = (item.user_id, item.pdf_product_id)
        if key in seen_pdf:
            item.delete()
        else:
            seen_pdf.add(key)


class Migration(migrations.Migration):
    dependencies = [("enrollments", "0002_certificate")]
    operations = [
        migrations.RunPython(clean_wishlist, migrations.RunPython.noop),
        migrations.AddConstraint(model_name="wishlist", constraint=models.CheckConstraint(check=(models.Q(course__isnull=False, pdf_product__isnull=True) | models.Q(course__isnull=True, pdf_product__isnull=False)), name="wishlist_exactly_one_target")),
        migrations.AddConstraint(model_name="wishlist", constraint=models.UniqueConstraint(fields=("user", "course"), condition=models.Q(course__isnull=False), name="uniq_wishlist_course")),
        migrations.AddConstraint(model_name="wishlist", constraint=models.UniqueConstraint(fields=("user", "pdf_product"), condition=models.Q(pdf_product__isnull=False), name="uniq_wishlist_pdf")),
    ]
