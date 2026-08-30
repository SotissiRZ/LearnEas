from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("catalog", "0003_course_certificates_lesson_accessibility")]
    operations = [
        migrations.AddIndex(model_name="course", index=models.Index(fields=["published", "category"], name="catalog_cou_publish_85f2cc_idx")),
        migrations.AddIndex(model_name="course", index=models.Index(fields=["instructor", "published"], name="catalog_cou_instruc_115d51_idx")),
        migrations.AddIndex(model_name="pdfproduct", index=models.Index(fields=["published", "category"], name="catalog_pdf_publish_8274ce_idx")),
        migrations.AddIndex(model_name="pdfproduct", index=models.Index(fields=["instructor", "published"], name="catalog_pdf_instruc_fbc105_idx")),
    ]
