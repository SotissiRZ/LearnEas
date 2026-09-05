from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("opportunities", "0002_promote_existing_employers"),
    ]

    operations = [
        migrations.AddField(model_name="employerprofile", name="tagline", field=models.CharField(blank=True, max_length=180)),
        migrations.AddField(model_name="employerprofile", name="linkedin_url", field=models.URLField(blank=True)),
        migrations.AddField(model_name="employerprofile", name="contact_email", field=models.EmailField(blank=True, max_length=254)),
        migrations.AddField(model_name="employerprofile", name="founded_year", field=models.PositiveSmallIntegerField(blank=True, null=True)),
        migrations.AddField(model_name="employerprofile", name="brand_color", field=models.CharField(blank=True, default="#ff5a1f", max_length=7)),
        migrations.AddField(model_name="employerprofile", name="banner", field=models.ImageField(blank=True, null=True, upload_to="employers/banners/%Y/%m/")),
        migrations.AddField(model_name="employerprofile", name="values", field=models.JSONField(blank=True, default=list)),
        migrations.AddField(model_name="employerprofile", name="benefits", field=models.JSONField(blank=True, default=list)),
        migrations.AddField(model_name="employerprofile", name="hiring_regions", field=models.JSONField(blank=True, default=list)),
        migrations.AddField(model_name="opportunity", name="department", field=models.CharField(blank=True, max_length=140)),
        migrations.AddField(model_name="opportunity", name="openings", field=models.PositiveSmallIntegerField(default=1)),
        migrations.AddField(model_name="opportunity", name="cover_image", field=models.ImageField(blank=True, null=True, upload_to="opportunities/covers/%Y/%m/")),
        migrations.AddField(model_name="opportunity", name="screening_questions", field=models.JSONField(blank=True, default=list)),
        migrations.AddField(model_name="opportunityapplication", name="screening_answers", field=models.JSONField(blank=True, default=list)),
        migrations.AddField(model_name="opportunityapplication", name="recruiter_rating", field=models.PositiveSmallIntegerField(default=0)),
        migrations.AddField(model_name="opportunityapplication", name="recruiter_tags", field=models.JSONField(blank=True, default=list)),
        migrations.AddField(model_name="opportunityapplication", name="next_step_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.CreateModel(
            name="TalentBookmark",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("note", models.TextField(blank=True)),
                ("tags", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("employer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="talent_bookmarks", to="opportunities.employerprofile")),
                ("talent", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="recruiter_bookmarks", to="opportunities.candidateprofile")),
            ],
            options={"ordering": ["-updated_at"]},
        ),
        migrations.AddConstraint(
            model_name="talentbookmark",
            constraint=models.UniqueConstraint(fields=("employer", "talent"), name="uniq_employer_talent_bookmark"),
        ),
        migrations.AddIndex(
            model_name="talentbookmark",
            index=models.Index(fields=["employer", "-updated_at"], name="opp_bookmark_employer_idx"),
        ),
    ]
