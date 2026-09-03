import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("formations", "0009_cohorts_and_mentorship"),
        ("payments", "0010_cinetpay_mobile_money"),
    ]

    operations = [
        migrations.AddField(
            model_name="orderitem",
            name="mentorship_booking",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="order_items", to="formations.mentorshipbooking"),
        ),
        migrations.AlterField(
            model_name="orderitem",
            name="item_type",
            field=models.CharField(choices=[("course", "Cours"), ("pdf", "PDF"), ("formation", "Formation interactive"), ("mentoring", "Mentorat")], max_length=10),
        ),
    ]
