from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("enrollments", "0007_lessonprogress_watch_heartbeat"),
        ("projects", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="portfolioprofile",
            name="show_certificates",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="portfolioprofile",
            name="public_contact_email",
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AddField(
            model_name="portfolioprofile",
            name="show_contact_email",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(model_name="portfolioitem", name="role", field=models.CharField(blank=True, max_length=180)),
        migrations.AddField(model_name="portfolioitem", name="problem", field=models.TextField(blank=True)),
        migrations.AddField(model_name="portfolioitem", name="objective", field=models.TextField(blank=True)),
        migrations.AddField(model_name="portfolioitem", name="outcome", field=models.TextField(blank=True)),
        migrations.AddField(model_name="portfolioitem", name="stack", field=models.JSONField(blank=True, default=list)),
        migrations.AddField(model_name="portfolioitem", name="video_url", field=models.URLField(blank=True)),
        migrations.AddField(model_name="portfolioitem", name="started_at", field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name="portfolioitem", name="completed_at", field=models.DateField(blank=True, null=True)),
        migrations.CreateModel(
            name="PortfolioCertificate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_public", models.BooleanField(db_index=True, default=True)),
                ("featured", models.BooleanField(default=False)),
                ("order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("certificate", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="portfolio_selections", to="enrollments.certificate")),
                ("profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="certificate_selections", to="projects.portfolioprofile")),
            ],
            options={"ordering": ["-featured", "order", "-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="portfoliocertificate",
            constraint=models.UniqueConstraint(fields=("profile", "certificate"), name="uniq_portfolio_profile_certificate"),
        ),
        migrations.AddIndex(
            model_name="portfoliocertificate",
            index=models.Index(fields=["profile", "is_public", "featured"], name="portfolio_cert_public_idx"),
        ),
    ]
