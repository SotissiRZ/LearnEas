from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.catalog.models import Category, Course, Section, Lesson, PDFResource, PDFProduct

User = get_user_model()


class Command(BaseCommand):
    help = "Génère des données de démonstration LearnEas"

    def handle(self, *args, **options):
        admin, _ = User.objects.get_or_create(
            username="admin", email="admin@learneas.com",
            defaults={"role": "admin", "is_staff": True, "is_superuser": True},
        )
        admin.set_password("admin1234")
        admin.save()

        instr, _ = User.objects.get_or_create(
            username="sarah_dev", email="sarah@learneas.com",
            defaults={"role": "instructor", "first_name": "Sarah", "last_name": "Benali",
                      "domain": "Développement web", "years_experience": 7,
                      "headline": "Développeuse Full-Stack — Django & React"},
        )
        instr.set_password("instructor1234")
        instr.save()

        cat, _ = Category.objects.get_or_create(name="Développement Web", defaults={"icon": "Code2"})
        cat2, _ = Category.objects.get_or_create(name="Data & IA", defaults={"icon": "BrainCircuit"})

        course, created = Course.objects.get_or_create(
            title="Django REST Framework de A à Z",
            defaults=dict(
                instructor=instr, category=cat,
                subtitle="Construisez des API robustes avec Django & DRF",
                description="Un cours complet pour maîtriser Django REST Framework, "
                             "de la modélisation à l'authentification JWT.",
                what_you_will_learn=["Modéliser une base de données", "Créer des API REST",
                                      "Authentification JWT", "Déployer en production"],
                requirements=["Bases de Python", "Notions HTML/CSS"],
                level="intermediate", language="Français",
                price=299, published=True, featured=True,
            ),
        )
        if created:
            s1 = Section.objects.create(course=course, title="Introduction", order=1)
            Lesson.objects.create(section=s1, title="Bienvenue dans le cours", duration_minutes=5, order=1, is_preview=True)
            Lesson.objects.create(section=s1, title="Installation de l'environnement", duration_minutes=12, order=2)
            s2 = Section.objects.create(course=course, title="Modèles & Base de données", order=2)
            Lesson.objects.create(section=s2, title="Créer ses premiers modèles", duration_minutes=20, order=1)
            Lesson.objects.create(section=s2, title="Migrations avancées", duration_minutes=18, order=2)
            PDFResource.objects.create(course=course, title="Cheat-sheet Django ORM", page_count=6, is_free_sample=True)

        PDFProduct.objects.get_or_create(
            title="Guide complet UML pour projets de fin d'études",
            defaults=dict(
                instructor=instr, category=cat, description="Modélisation UML pas à pas.",
                level="beginner", price=49, page_count=42, published=True, featured=True,
            ),
        )

        self.stdout.write(self.style.SUCCESS("Données de démonstration créées avec succès."))
        self.stdout.write("Admin: admin@learneas.com / admin1234")
        self.stdout.write("Instructeur: sarah@learneas.com / instructor1234")
