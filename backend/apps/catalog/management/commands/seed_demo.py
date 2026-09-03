from datetime import timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.catalog.models import Category, Course, Section, Lesson, PDFResource, PDFProduct
from apps.formations.models import InteractiveFormation, FormationSession
from apps.reviews.models import Review
from apps.enrollments.models import CourseEnrollment
from apps.enrollments.certificates import issue_course_certificate
from apps.faq.models import FAQ

User = get_user_model()


class Command(BaseCommand):
    help = "Génère des données de démonstration complètes pour LearnEas (Afrique)"

    def handle(self, *args, **options):
        self.stdout.write("Création des utilisateurs...")
        admin = self._user("admin", "admin@learneas.com", "admin1234", role="admin",
                            is_staff=True, is_superuser=True, first_name="Admin", last_name="LearnEas")

        sarah = self._user(
            "sarah_dev", "sarah@learneas.com", "instructor1234", role="instructor",
            first_name="Sarah", last_name="Benali", country="Maroc",
            domain="Développement web", years_experience=7,
            headline="Développeuse Full-Stack · Django & React",
        )
        koffi = self._user(
            "koffi_data", "koffi@learneas.com", "instructor1234", role="instructor",
            first_name="Koffi", last_name="Adjei", country="Côte d'Ivoire",
            domain="Data & Intelligence Artificielle", years_experience=6,
            headline="Data Scientist · Python & Machine Learning",
        )
        amina = self._user(
            "amina_design", "amina@learneas.com", "instructor1234", role="instructor",
            first_name="Amina", last_name="Diop", country="Sénégal",
            domain="Design & UI/UX", years_experience=5,
            headline="Designer UI/UX freelance",
        )

        students = [
            self._user("student_fatou", "fatou@learneas.com", "student1234", role="student",
                       first_name="Fatou", last_name="Ndiaye", country="Sénégal"),
            self._user("student_jean", "jean@learneas.com", "student1234", role="student",
                       first_name="Jean", last_name="Mbeki", country="Cameroun"),
            self._user("student_aicha", "aicha@learneas.com", "student1234", role="student",
                       first_name="Aïcha", last_name="Traoré", country="Mali"),
        ]

        self.stdout.write("Création des catégories...")
        cat_web = self._category("Développement Web", "Code2")
        cat_data = self._category("Data & IA", "BrainCircuit")
        cat_design = self._category("Design & Infographie", "PenTool")
        cat_gestion = self._category("Gestion de projet", "ClipboardList")
        cat_reseaux = self._category("Réseaux & Systèmes", "Network")
        cat_bureautique = self._category("Bureautique", "FileSpreadsheet")

        self.stdout.write("Création des cours (playlists complètes)...")
        c1 = self._course(
            sarah, cat_web, "Django REST Framework de A à Z",
            "Construisez des API robustes avec Django & DRF",
            "Un cours complet pour maîtriser Django REST Framework, de la modélisation à "
            "l'authentification JWT, avec déploiement en production.",
            ["Modéliser une base de données", "Créer des API REST", "Authentification JWT",
             "Déployer en production"],
            ["Bases de Python", "Notions HTML/CSS"], "intermediate", 27.51, featured=True,
            sections=[
                ("Introduction", [
                    ("Bienvenue dans le cours", 5, True),
                    ("Installation de l'environnement", 12, False),
                ]),
                ("Modèles & Base de données", [
                    ("Créer ses premiers modèles", 20, False),
                    ("Migrations avancées", 18, False),
                    ("Relations et requêtes complexes", 22, False),
                ]),
                ("API REST avec DRF", [
                    ("Serializers et ViewSets", 25, False),
                    ("Authentification JWT", 20, False),
                    ("Permissions et sécurité", 15, False),
                ]),
            ],
            pdfs=[("Cheat-sheet Django ORM", 6, True), ("Guide de déploiement en production", 18, False)],
        )
        c2 = self._course(
            sarah, cat_web, "Next.js & TypeScript pour développeurs React",
            "Créez des applications web modernes et performantes",
            "Maîtrisez Next.js 14, l'App Router, le rendu serveur et TypeScript pour construire "
            "des applications web professionnelles.",
            ["App Router de Next.js", "Server Components", "TypeScript avancé", "Déploiement"],
            ["Bases de React", "JavaScript ES6+"], "intermediate", 32.11,
            sections=[
                ("Les fondamentaux", [
                    ("Pourquoi Next.js ?", 8, True),
                    ("App Router en détail", 20, False),
                ]),
                ("Server Components", [
                    ("Rendu côté serveur", 25, False),
                    ("Data fetching avancé", 20, False),
                ]),
            ],
        )
        c3 = self._course(
            koffi, cat_data, "Python pour la Data Science",
            "De zéro à l'analyse de données avec Python",
            "Apprenez Python, Pandas, NumPy et la visualisation de données pour démarrer une "
            "carrière en Data Science.",
            ["Manipulation de données avec Pandas", "Visualisation avec Matplotlib",
             "Statistiques descriptives", "Premiers modèles de Machine Learning"],
            ["Aucun prérequis"], "beginner", 22.91, featured=True,
            sections=[
                ("Bases de Python", [
                    ("Introduction à Python", 15, True),
                    ("Structures de données", 18, False),
                ]),
                ("Pandas & NumPy", [
                    ("Manipuler des DataFrames", 22, False),
                    ("Nettoyage de données", 20, False),
                ]),
                ("Machine Learning", [
                    ("Premier modèle avec Scikit-learn", 28, False),
                ]),
            ],
        )
        c4 = self._course(
            koffi, cat_data, "Machine Learning appliqué",
            "Construisez vos premiers modèles prédictifs",
            "Cours pratique sur les algorithmes de Machine Learning les plus utilisés en entreprise.",
            ["Régression et classification", "Arbres de décision", "Évaluation de modèles"],
            ["Python pour la Data Science (recommandé)"], "expert", 36.71,
            sections=[("Modèles supervisés", [("Régression linéaire", 20, True), ("Classification", 25, False)])],
        )
        c5 = self._course(
            amina, cat_design, "Photoshop pour débutants",
            "Maîtrisez la retouche photo et le design graphique",
            "Un cours accessible pour apprendre les fondamentaux de Photoshop, de la retouche "
            "photo à la création de visuels pour les réseaux sociaux.",
            ["Retouche photo professionnelle", "Créer des visuels réseaux sociaux", "Travailler les calques"],
            ["Aucun prérequis"], "beginner", 0, is_free=True,
            sections=[("Prise en main", [("Interface de Photoshop", 10, True), ("Les calques", 15, True)])],
        )
        c6 = self._course(
            amina, cat_design, "UI/UX Design avec Figma",
            "Concevez des interfaces modernes et intuitives",
            "Apprenez à concevoir des maquettes professionnelles avec Figma, du wireframe au prototype interactif.",
            ["Wireframing", "Design system", "Prototypage interactif"],
            ["Aucun prérequis"], "intermediate", 25.67, featured=True,
            sections=[("Les fondamentaux du design", [("Principes UI/UX", 15, True), ("Prise en main de Figma", 20, False)])],
        )
        c7 = self._course(
            sarah, cat_gestion, "Gestion de projet Agile & Scrum",
            "Pilotez vos projets comme un chef de projet certifié",
            "Découvrez les méthodologies Agile et Scrum pour gérer efficacement vos projets informatiques.",
            ["Framework Scrum", "Rédiger un backlog", "Animer des sprints"],
            ["Aucun prérequis"], "beginner", 18.31,
            sections=[("Introduction à l'Agilité", [("Les principes Agile", 12, True), ("Le rôle du Scrum Master", 15, False)])],
        )
        c8 = self._course(
            koffi, cat_reseaux, "Administration Linux pour débutants",
            "Les bases indispensables de l'administration système",
            "Ligne de commande, gestion des utilisateurs, réseaux : tout pour administrer un serveur Linux.",
            ["Ligne de commande avancée", "Gestion des utilisateurs et permissions", "Bases réseau"],
            ["Notions d'informatique générales"], "beginner", 17.39,
            sections=[("Prise en main", [("Introduction au terminal", 10, True), ("Gestion des fichiers", 15, False)])],
        )

        self.stdout.write("Création des PDF vendus seuls...")
        self._pdf(sarah, cat_gestion, "Guide complet UML pour projets de fin d'études",
                  "Modélisation UML pas à pas : diagrammes de cas d'utilisation, de séquence, "
                  "de classes... Idéal pour vos projets académiques.", "beginner", 4.51, 42, featured=True)
        self._pdf(koffi, cat_data, "100 exercices corrigés de Python",
                  "Une collection d'exercices pratiques avec corrections détaillées pour progresser en Python.",
                  "beginner", 3.59, 60, featured=True)
        self._pdf(amina, cat_design, "Charte graphique : le guide complet",
                  "Comment construire une charte graphique professionnelle de A à Z.", "intermediate", 5.43, 35)
        self._pdf(sarah, cat_web, "Aide-mémoire Git & GitHub", "Toutes les commandes Git essentielles "
                  "réunies dans un seul document.", "beginner", 0, 10, is_free=True)

        self.stdout.write("Création des formations interactives...")
        now = timezone.now()

        f1 = InteractiveFormation.objects.get_or_create(
            title="Coaching React avancé en petit groupe",
            defaults=dict(
                instructor=sarah, category=cat_web,
                description="Sessions live de mentoring pour maîtriser les hooks avancés, "
                             "la gestion d'état et les bonnes pratiques React en petit groupe.",
                level="intermediate", price=13.80, num_sessions=4, session_duration_minutes=90,
                max_students=6, status="scheduled", published=True,
                start_date=(now + timedelta(days=7)).date(),
                end_date=(now + timedelta(days=28)).date(),
            ),
        )[0]
        for i in range(1, 5):
            FormationSession.objects.get_or_create(
                formation=f1, session_number=i,
                defaults=dict(
                    scheduled_at=now + timedelta(days=7 * i, hours=18),
                    duration_minutes=90,
                    meeting_link="",
                ),
            )

        f2 = InteractiveFormation.objects.get_or_create(
            title="Atelier Data Science : de la théorie à la pratique",
            defaults=dict(
                instructor=koffi, category=cat_data,
                description="Un atelier intensif en 3 séances pour appliquer vos connaissances en "
                             "Data Science sur un vrai projet, avec correction personnalisée.",
                level="intermediate", price=20.24, num_sessions=3, session_duration_minutes=120,
                max_students=8, status="scheduled", published=True,
                start_date=(now + timedelta(days=10)).date(),
                end_date=(now + timedelta(days=24)).date(),
            ),
        )[0]
        for i in range(1, 4):
            FormationSession.objects.get_or_create(
                formation=f2, session_number=i,
                defaults=dict(
                    scheduled_at=now + timedelta(days=10 + 7 * i, hours=17),
                    duration_minutes=120,
                    meeting_link="",
                ),
            )

        f3 = InteractiveFormation.objects.get_or_create(
            title="Design Thinking pour porteurs de projet",
            defaults=dict(
                instructor=amina, category=cat_design,
                description="Formation en direct pour apprendre à structurer une démarche de "
                             "Design Thinking et concevoir un premier prototype de votre idée.",
                level="beginner", price=8.28, num_sessions=2, session_duration_minutes=60,
                max_students=10, status="scheduled", published=True,
                start_date=(now + timedelta(days=5)).date(),
                end_date=(now + timedelta(days=12)).date(),
            ),
        )[0]
        for i in range(1, 3):
            FormationSession.objects.get_or_create(
                formation=f3, session_number=i,
                defaults=dict(
                    scheduled_at=now + timedelta(days=5 + 7 * i, hours=19),
                    duration_minutes=60,
                    meeting_link="",
                ),
            )

        self.stdout.write("Création des avis...")
        reviews_data = [
            (students[0], c1, 5, "Excellent cours, très bien expliqué, je recommande !"),
            (students[1], c1, 4, "Très complet, quelques passages un peu rapides."),
            (students[2], c3, 5, "Parfait pour débuter en Data Science."),
            (students[0], c6, 5, "Amina explique très clairement, j'ai adoré."),
        ]
        for user, course, rating, comment in reviews_data:
            review, created = Review.objects.get_or_create(
                user=user, course=course, defaults={"rating": rating, "comment": comment}
            )
            if created:
                qs = Review.objects.filter(course=course)
                count = qs.count()
                avg = sum(r.rating for r in qs) / count if count else 0
                course.rating_avg = round(avg, 2)
                course.rating_count = count
                course.save(update_fields=["rating_avg", "rating_count"])

        self.stdout.write("Création d'un certificat de démonstration...")
        fatou_enrollment, _ = CourseEnrollment.objects.get_or_create(user=students[0], course=c1)
        fatou_enrollment.progress_percent = 100
        fatou_enrollment.completed = True
        fatou_enrollment.completed_at = fatou_enrollment.completed_at or timezone.now()
        fatou_enrollment.save(update_fields=["progress_percent", "completed", "completed_at"])
        issue_course_certificate(fatou_enrollment, issued_by=sarah, force=True)

        self.stdout.write("Création de la FAQ...")
        faq_items = [
            ("Comment payer avec Mobile Money ?",
             "Lors du paiement, sélectionnez Mobile Money puis votre opérateur (Orange Money, "
             "MTN MoMo, Wave ou M-Pesa). Vous recevrez une demande de confirmation sur votre téléphone."),
            ("Ai-je accès au cours à vie après achat ?",
             "Oui, l'accès à un cours acheté est illimité dans le temps, sans abonnement."),
            ("Comment fonctionne une formation interactive ?",
             "Une formation interactive se déroule en direct par visioconférence, en petit groupe, "
             "selon un planning de séances défini par l'instructeur."),
            ("Puis-je devenir instructeur sur LearnEas ?",
             "Oui, rendez-vous dans votre tableau de bord puis 'Devenir instructeur' pour publier "
             "vos propres cours, PDF et formations interactives."),
            ("Le certificat est-il reconnu ?",
             "Le certificat atteste de la complétion du cours sur la plateforme. Il valorise vos "
             "compétences acquises mais n'est pas un diplôme officiel."),
        ]
        for question, answer in faq_items:
            FAQ.objects.get_or_create(question=question, defaults={"answer": answer, "author": admin})

        self.stdout.write(self.style.SUCCESS("\n\u2714 Données de démonstration créées avec succès.\n"))
        self.stdout.write("Comptes disponibles (mot de passe entre parenthèses) :")
        self.stdout.write("  Admin........... admin@learneas.com (admin1234)")
        self.stdout.write("  Instructeur..... sarah@learneas.com (instructor1234) · Dév. web")
        self.stdout.write("  Instructeur..... koffi@learneas.com (instructor1234) · Data & IA")
        self.stdout.write("  Instructeur..... amina@learneas.com (instructor1234) · Design")
        self.stdout.write("  Étudiant........ fatou@learneas.com (student1234)")
        self.stdout.write("  Étudiant........ jean@learneas.com (student1234)")
        self.stdout.write("  Étudiant........ aicha@learneas.com (student1234)")

    # ------------------------------------------------------------------ helpers
    def _user(self, username, email, password, role, **extra):
        user, _ = User.objects.get_or_create(username=username, defaults={"email": email, "role": role, **extra})
        user.email = email
        user.role = role
        for k, v in extra.items():
            setattr(user, k, v)
        user.set_password(password)
        user.save()
        return user

    def _category(self, name, icon):
        cat, _ = Category.objects.get_or_create(name=name, defaults={"icon": icon})
        return cat

    def _course(self, instructor, category, title, subtitle, description, learn, requirements,
                level, price, is_free=False, featured=False, sections=None, pdfs=None):
        course, created = Course.objects.get_or_create(
            title=title,
            defaults=dict(
                instructor=instructor, category=category, subtitle=subtitle, description=description,
                what_you_will_learn=learn, requirements=requirements, level=level, language="Français",
                price=price, is_free=is_free, published=True, featured=featured,
            ),
        )
        if created:
            for order, (section_title, lessons) in enumerate(sections or [], start=1):
                section = Section.objects.create(course=course, title=section_title, order=order)
                for l_order, (l_title, duration, preview) in enumerate(lessons, start=1):
                    Lesson.objects.create(
                        section=section, title=l_title, duration_minutes=duration,
                        order=l_order, is_preview=preview,
                    )
            for order, (pdf_title, pages, free_sample) in enumerate(pdfs or [], start=1):
                PDFResource.objects.create(
                    course=course, title=pdf_title, page_count=pages,
                    is_free_sample=free_sample, order=order,
                )
        return course

    def _pdf(self, instructor, category, title, description, level, price, pages,
             is_free=False, featured=False):
        PDFProduct.objects.get_or_create(
            title=title,
            defaults=dict(
                instructor=instructor, category=category, description=description, level=level,
                price=price, is_free=is_free, page_count=pages, published=True, featured=featured,
            ),
        )
