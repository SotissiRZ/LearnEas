from django.db import migrations, models


def clean_invalid_reviews(apps, schema_editor):
    Review = apps.get_model("reviews", "Review")
    Review.objects.filter(course__isnull=True, pdf_product__isnull=True).delete()
    Review.objects.filter(course__isnull=False, pdf_product__isnull=False).update(pdf_product=None)


class Migration(migrations.Migration):
    dependencies = [("reviews", "0001_initial")]
    operations = [
        migrations.RunPython(clean_invalid_reviews, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="review",
            constraint=models.CheckConstraint(
                check=(models.Q(course__isnull=False, pdf_product__isnull=True) | models.Q(course__isnull=True, pdf_product__isnull=False)),
                name="review_exactly_one_target",
            ),
        ),
    ]
