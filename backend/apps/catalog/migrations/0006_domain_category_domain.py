from django.db import migrations, models
import django.db.models.deletion


def seed_domains(apps, schema_editor):
    Domain = apps.get_model("catalog", "Domain")
    Category = apps.get_model("catalog", "Category")

    definitions = [
        ("Technologie & Numérique", "technologie-numerique", "Code2", 10),
        ("Data & IA", "data-ia", "BrainCircuit", 20),
        ("Design & Création", "design-creation", "Palette", 30),
        ("Business & Gestion", "business-gestion", "BriefcaseBusiness", 40),
        ("Bureautique & Productivité", "bureautique-productivite", "FileSpreadsheet", 50),
        ("Autres domaines", "autres-domaines", "Layers3", 90),
    ]
    domains = {}
    for name, slug, icon, order in definitions:
        domain, _ = Domain.objects.get_or_create(
            slug=slug,
            defaults={"name": name, "icon": icon, "order": order},
        )
        domains[slug] = domain

    explicit = {
        "Développement Web": "technologie-numerique",
        "Réseaux & Systèmes": "technologie-numerique",
        "Data & IA": "data-ia",
        "Design & Infographie": "design-creation",
        "Gestion de projet": "business-gestion",
        "Bureautique": "bureautique-productivite",
    }
    for category in Category.objects.all().iterator():
        target = explicit.get(category.name)
        if not target:
            name = category.name.lower()
            if any(word in name for word in ("data", "ia", "machine", "intelligence")):
                target = "data-ia"
            elif any(word in name for word in ("design", "graph", "créa", "ux", "ui")):
                target = "design-creation"
            elif any(word in name for word in ("business", "gestion", "marketing", "vente", "finance", "management")):
                target = "business-gestion"
            elif any(word in name for word in ("bureaut", "excel", "word", "office", "productiv")):
                target = "bureautique-productivite"
            elif any(word in name for word in ("web", "dévelop", "code", "réseau", "système", "cloud", "cyber")):
                target = "technologie-numerique"
            else:
                target = "autres-domaines"
        category.domain_id = domains[target].id
        category.save(update_fields=["domain"])


def reverse_seed(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    Category.objects.update(domain=None)


class Migration(migrations.Migration):
    dependencies = [("catalog", "0005_lesson_adaptive_streaming")]

    operations = [
        migrations.CreateModel(
            name="Domain",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, unique=True)),
                ("slug", models.SlugField(blank=True, max_length=120, unique=True)),
                ("icon", models.CharField(default="Layers3", help_text="Nom d'icône lucide-react (ex: Code2, BrainCircuit, Palette, BriefcaseBusiness)", max_length=50)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("order", models.PositiveSmallIntegerField(default=0)),
            ],
            options={"ordering": ["order", "name"]},
        ),
        migrations.AddField(
            model_name="category",
            name="domain",
            field=models.ForeignKey(blank=True, help_text="Domaine principal utilisé pour les filtres du catalogue.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="categories", to="catalog.domain"),
        ),
        migrations.RunPython(seed_domains, reverse_seed),
    ]
