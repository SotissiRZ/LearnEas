from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("formations", "0012_cohort_waitlist_mentorship_ops"),
        ("payments", "0014_payment_operations_audit"),
    ]

    operations = [
        migrations.AlterField(
            model_name="orderitem",
            name="item_type",
            field=models.CharField(choices=[("course", "Cours"), ("pdf", "PDF"), ("formation", "Formation interactive"), ("mentoring", "Mentorat"), ("mentor_pack", "Pack mentorat"), ("employer", "Droit recruteur")], max_length=20),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="mentorship_pack",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="order_items", to="formations.mentorshippack"),
        ),
    ]
