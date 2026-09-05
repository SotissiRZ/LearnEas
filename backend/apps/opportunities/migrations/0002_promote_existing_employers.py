from django.db import migrations


def promote_existing_employers(apps, schema_editor):
    EmployerProfile = apps.get_model("opportunities", "EmployerProfile")
    User = apps.get_model("accounts", "User")
    user_ids = EmployerProfile.objects.values_list("user_id", flat=True)
    # Préserve les comptes admin/instructeur qui auraient aussi un profil entreprise ;
    # seuls les anciens recruteurs modélisés comme étudiants sont promus.
    User.objects.filter(id__in=user_ids, role="student").update(role="employer")


def reverse_promote_existing_employers(apps, schema_editor):
    EmployerProfile = apps.get_model("opportunities", "EmployerProfile")
    User = apps.get_model("accounts", "User")
    user_ids = EmployerProfile.objects.values_list("user_id", flat=True)
    User.objects.filter(id__in=user_ids, role="employer").update(role="student")


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0010_user_employer_role"),
        ("opportunities", "0001_initial"),
    ]
    operations = [migrations.RunPython(promote_existing_employers, reverse_promote_existing_employers)]
