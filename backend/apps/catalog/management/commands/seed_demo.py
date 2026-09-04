from datetime import timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.catalog.models import Domain, Category, Course, Section, Lesson, PDFResource, PDFProduct
from apps.formations.models import InteractiveFormation, FormationSession, MentorshipOffering
from apps.reviews.models import Review
from apps.enrollments.models import CourseEnrollment
from apps.enrollments.certificates import issue_course_certificate
from apps.faq.models import FAQ
from apps.projects.models import ProjectAssignment, ProjectSubmission
from apps.projects.services import ensure_portfolio_profile, publish_verified_submission
from apps.opportunities.models import EmployerProfile, CandidateProfile, Opportunity, OpportunityApplication
from apps.opportunities.services import build_application_snapshot

User = get_user_model()


class Command(BaseCommand):
    help = "Génère des données de démonstration complètes pour KalanPro (Afrique)"

    def handle(self, *args, **options):
        self.stdout.write("Création des utilisateurs...")
        admin = self._user("admin", "admin@kalanpro.com", "admin1234", role="admin",
                            is_staff=True, is_superuser=True, first_name="Admin", last_name="KalanPro")

        sarah = self._user(
            "sarah_dev", "sarah@kalanpro.com", "instructor1234", role="instructor",
            first_name="Sarah", last_name="Benali", country="Maroc",
            domain="Développement web", years_experience=7,
            headline="Développeuse Full-Stack · Django & React",
        )
        koffi = self._user(
            "koffi_data", "koffi@kalanpro.com", "instructor1234", role="instructor",
            first_name="Koffi", last_name="Adjei", country="Côte d'Ivoire",
            domain="Data & Intelligence Artificielle", years_experience=6,
            headline="Data Scientist · Python & Machine Learning",
        )
        amina = self._user(
            "amina_design", "amina@kalanpro.com", "instructor1234", role="instructor",
            first_name="Amina", last_name="Diop", country="Sénégal",
            domain="Design & UI/UX", years_experience=5,
            headline="Designer UI/UX freelance",
        )

        students = [
            self._user("student_fatou", "fatou@kalanpro.com", "student1234", role="student",
                       first_name="Fatou", last_name="Ndiaye", country="Sénégal"),
            self._user("student_jean", "jean@kalanpro.com", "student1234", role="student",
                       first_name="Jean", last_name="Mbeki", country="Cameroun"),
            self._user("student_aicha", "aicha@kalanpro.com", "student1234", role="student",
                       first_name="Aïcha", last_name="Traoré", country="Mali"),
        ]

        recruiter = self._user(
            "recruiter_demo", "recruteur@kalanpro.com", "recruiter1234", role="student",
            first_name="Moussa", last_name="Koné", country="Côte d'Ivoire",
            headline="Responsable recrutement · Demo Digital Africa",
        )
        demo_employer, _ = EmployerProfile.objects.get_or_create(
            user=recruiter,
            defaults={
                "company_name": "Demo Digital Africa", "country": "Côte d'Ivoire", "city": "Abidjan",
                "industry": "Services numériques", "company_size": "11-50",
                "description": "PME numérique de démonstration recrutant des profils francophones à distance et en Afrique de l'Ouest.",
                "website_url": "https://example.com", "status": EmployerProfile.Status.APPROVED,
                "reviewed_by": admin, "reviewed_at": timezone.now(),
            },
        )
        if demo_employer.status != EmployerProfile.Status.APPROVED:
            demo_employer.status = EmployerProfile.Status.APPROVED
            demo_employer.reviewed_by = admin
            demo_employer.reviewed_at = timezone.now()
            demo_employer.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])

        self.stdout.write("Création des domaines et catégories...")
        dom_tech = self._domain("Technologie & Numérique", "Code2", 10)
        dom_data = self._domain("Data & IA", "BrainCircuit", 20)
        dom_design = self._domain("Design & Création", "Palette", 30)
        dom_business = self._domain("Business & Gestion", "BriefcaseBusiness", 40)
        dom_productivity = self._domain("Bureautique & Productivité", "FileSpreadsheet", 50)

        cat_web = self._category("Développement Web", "Code2", dom_tech)
        cat_data = self._category("Data & IA", "BrainCircuit", dom_data)
        cat_design = self._category("Design & Infographie", "PenTool", dom_design)
        cat_gestion = self._category("Gestion de projet", "ClipboardList", dom_business)
        cat_reseaux = self._category("Réseaux & Systèmes", "Network", dom_tech)
        cat_bureautique = self._category("Bureautique", "FileSpreadsheet", dom_productivity)

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

        # Métadonnées de cohorte v45 : les get_or_create ci-dessus conservent aussi les bases
        # créées par les anciennes versions du seed. On met donc ces champs à jour explicitement.
        cohort_meta = [
            (f1, "Cohorte React · Septembre", 3, now + timedelta(days=6)),
            (f2, "Cohorte Data · Septembre", 4, now + timedelta(days=9)),
            (f3, "Cohorte Design · Septembre", 4, now + timedelta(days=4)),
        ]
        for formation, cohort_name, minimum, deadline in cohort_meta:
            formation.cohort_name = cohort_name
            formation.cohort_timezone = "Africa/Abidjan"
            formation.min_students = minimum
            formation.enrollment_deadline = deadline
            formation.status = "scheduled"
            formation.published = True
            formation.save(update_fields=[
                "cohort_name", "cohort_timezone", "min_students", "enrollment_deadline", "status", "published"
            ])

        self.stdout.write("Création des offres de mentorat...")
        from apps.formations.mentorship import create_slot, ensure_room_formation
        mentor_offers = [
            (koffi, "Mentorat Data & carrière", "Séance individuelle pour débloquer un projet data, préparer un entretien ou structurer votre progression.", 45, 13.80),
            (amina, "Revue portfolio UI/UX", "Relecture de portfolio et recommandations concrètes pour présenter vos projets à un recruteur ou à un client.", 30, 9.20),
        ]
        for mentor, title, description, duration, price in mentor_offers:
            offer, _ = MentorshipOffering.objects.get_or_create(
                instructor=mentor, title=title,
                defaults={
                    "description": description, "duration_minutes": duration, "price": price,
                    "language": "Français", "timezone": "Africa/Abidjan",
                    "booking_notice_hours": 2, "cancellation_notice_hours": 12, "published": True,
                },
            )
            if not offer.published:
                offer.published = True
                offer.save(update_fields=["published", "updated_at"])
            ensure_room_formation(offer)
            if not offer.slots.filter(is_active=True, starts_at__gt=now).exists():
                create_slot(offer, now + timedelta(days=3, hours=3))
                create_slot(offer, now + timedelta(days=5, hours=5))

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

        fatou_enrollment, _ = CourseEnrollment.objects.get_or_create(user=students[0], course=c1)
        fatou_enrollment.progress_percent = 100
        fatou_enrollment.completed = True
        fatou_enrollment.completed_at = fatou_enrollment.completed_at or timezone.now()
        fatou_enrollment.save(update_fields=["progress_percent", "completed", "completed_at"])

        self.stdout.write("Création d'un projet et portfolio de démonstration...")
        demo_project, _ = ProjectAssignment.objects.get_or_create(
            course=c1, title="API de gestion de bibliothèque",
            defaults={
                "brief": "Concevez une API REST pour gérer livres, auteurs, emprunts et authentification.",
                "instructions": "Documentez les endpoints, ajoutez les permissions et expliquez vos choix techniques.",
                "objectives": ["Modéliser les relations", "Sécuriser l'API", "Documenter les endpoints"],
                "deliverables": ["Code source ou archive", "README", "Présentation de l'architecture"],
                "skills": ["Django", "Django REST Framework", "API REST", "JWT"],
                "max_score": 100, "passing_score": 60, "required_for_certificate": False,
                "allow_resubmission": True, "published": True, "order": 1,
            },
        )
        demo_submission, _ = ProjectSubmission.objects.get_or_create(
            assignment=demo_project, student=students[0],
            defaults={
                "enrollment": fatou_enrollment, "title": "Bibliothèque API",
                "summary": "API REST complète avec permissions par rôle, JWT et documentation des principaux endpoints.",
                "skills": ["Django", "DRF", "JWT"], "status": ProjectSubmission.Status.APPROVED,
                "score": 92, "instructor_feedback": "Architecture claire et permissions correctement appliquées.",
                "submitted_at": timezone.now(), "reviewed_at": timezone.now(), "reviewed_by": sarah,
            },
        )
        if demo_submission.status == ProjectSubmission.Status.APPROVED:
            publish_verified_submission(demo_submission)
        demo_profile = ensure_portfolio_profile(students[0])
        demo_profile.is_public = True
        demo_profile.title = "Développeuse backend junior · Django & API REST"
        demo_profile.about = "Je construis des API web structurées et je développe mon portfolio à travers des projets pratiques KalanPro."
        demo_profile.skills = ["Python", "Django", "Django REST Framework", "API REST"]
        demo_profile.open_to_work = True
        demo_profile.save()

        # Émettre le certificat après la validation du projet afin que le snapshot v47
        # embarque réellement les compétences et la preuve pratique du compte de démo.
        self.stdout.write("Création d'un certificat vérifiable de démonstration...")
        issue_course_certificate(fatou_enrollment, issued_by=sarah, force=True)

        self.stdout.write("Création des opportunités professionnelles de démonstration...")
        CandidateProfile.objects.update_or_create(
            user=students[0],
            defaults={
                "headline": "Développeuse backend junior · Django & API REST",
                "summary": "Je recherche un premier poste ou une mission backend en environnement francophone.",
                "skills": ["Python", "Django", "Django REST Framework", "API REST", "JWT"],
                "desired_roles": ["Développeuse backend junior", "Développeuse Python"],
                "preferred_kinds": ["job", "internship", "mission"],
                "preferred_work_modes": ["remote", "hybrid"],
                "preferred_countries": ["Sénégal", "Côte d'Ivoire"],
                "availability": CandidateProfile.Availability.IMMEDIATE,
                "years_experience": 1, "is_searchable": True,
            },
        )
        demo_job, _ = Opportunity.objects.get_or_create(
            employer=demo_employer, title="Développeur·se Python / Django junior",
            defaults={
                "kind": Opportunity.Kind.JOB, "contract_type": Opportunity.ContractType.FULL_TIME,
                "work_mode": Opportunity.WorkMode.REMOTE, "experience_level": Opportunity.ExperienceLevel.JUNIOR,
                "description": "Rejoignez une équipe produit pour développer des API et services web adaptés aux marchés africains francophones.",
                "responsibilities": ["Développer des API REST", "Corriger et tester les fonctionnalités", "Participer aux revues de code"],
                "requirements": ["Bonnes bases Python", "Compréhension de Django", "Capacité à travailler en équipe"],
                "skills_required": ["Python", "Django", "API REST"],
                "skills_optional": ["PostgreSQL", "Docker", "Git"],
                "remote_worldwide": True, "salary_min": 450000, "salary_max": 700000,
                "salary_currency": "XOF", "salary_period": Opportunity.SalaryPeriod.MONTH,
                "show_salary": True, "status": Opportunity.Status.PUBLISHED,
                "application_deadline": timezone.now() + timedelta(days=30),
            },
        )
        Opportunity.objects.get_or_create(
            employer=demo_employer, title="Mission freelance · Tableau de bord Power BI",
            defaults={
                "kind": Opportunity.Kind.MISSION, "contract_type": Opportunity.ContractType.PROJECT,
                "work_mode": Opportunity.WorkMode.REMOTE, "experience_level": Opportunity.ExperienceLevel.JUNIOR,
                "description": "Mission courte pour construire un tableau de bord commercial à partir de fichiers Excel.",
                "responsibilities": ["Nettoyer les données", "Créer les indicateurs", "Présenter le tableau de bord"],
                "requirements": ["Portfolio ou projet démontrable"],
                "skills_required": ["Excel", "Power BI"], "skills_optional": ["DAX"],
                "remote_worldwide": True, "salary_min": 150000, "salary_max": 250000,
                "salary_currency": "XOF", "salary_period": Opportunity.SalaryPeriod.PROJECT,
                "status": Opportunity.Status.PUBLISHED, "application_deadline": timezone.now() + timedelta(days=21),
            },
        )
        if not OpportunityApplication.objects.filter(opportunity=demo_job, candidate=students[0]).exists():
            snapshot = build_application_snapshot(students[0], demo_job, share_portfolio=True)
            OpportunityApplication.objects.create(
                opportunity=demo_job, candidate=students[0], cover_letter="Je souhaite mettre en pratique mes compétences Django sur un produit à impact régional.",
                share_portfolio=True, **snapshot,
            )

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
            ("Puis-je devenir instructeur sur KalanPro ?",
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
        self.stdout.write("  Admin........... admin@kalanpro.com (admin1234)")
        self.stdout.write("  Instructeur..... sarah@kalanpro.com (instructor1234) · Dév. web")
        self.stdout.write("  Instructeur..... koffi@kalanpro.com (instructor1234) · Data & IA")
        self.stdout.write("  Instructeur..... amina@kalanpro.com (instructor1234) · Design")
        self.stdout.write("  Étudiant........ fatou@kalanpro.com (student1234)")
        self.stdout.write("  Étudiant........ jean@kalanpro.com (student1234)")
        self.stdout.write("  Étudiant........ aicha@kalanpro.com (student1234)")
        self.stdout.write("  Recruteur....... recruteur@kalanpro.com (recruiter1234) · Demo Digital Africa")

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

    def _domain(self, name, icon, order):
        domain, _ = Domain.objects.get_or_create(name=name, defaults={"icon": icon, "order": order})
        changed = False
        if domain.icon != icon:
            domain.icon = icon
            changed = True
        if domain.order != order:
            domain.order = order
            changed = True
        if changed:
            domain.save(update_fields=["icon", "order"])
        return domain

    def _category(self, name, icon, domain=None):
        cat, _ = Category.objects.get_or_create(name=name, defaults={"icon": icon, "domain": domain})
        changed = False
        if cat.icon != icon:
            cat.icon = icon
            changed = True
        if domain and cat.domain_id != domain.id:
            cat.domain = domain
            changed = True
        if changed:
            cat.save(update_fields=["icon", "domain"])
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
