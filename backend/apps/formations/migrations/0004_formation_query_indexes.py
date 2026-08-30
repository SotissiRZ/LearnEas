from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("formations", "0003_formation_certificates")]
    operations = [
        migrations.AddIndex(model_name="interactiveformation", index=models.Index(fields=["published", "status"], name="formations_publish_2be0cf_idx")),
        migrations.AddIndex(model_name="interactiveformation", index=models.Index(fields=["instructor", "published"], name="formations_instruc_9bcd81_idx")),
    ]
