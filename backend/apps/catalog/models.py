from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator


class Domain(models.Model):
    """Grand domaine métier utilisé pour regrouper plusieurs catégories du catalogue."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    icon = models.CharField(
        max_length=50, default="Layers3",
        help_text="Nom d'icône lucide-react (ex: Code2, BrainCircuit, Palette, BriefcaseBusiness)",
    )
    description = models.CharField(max_length=255, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Category(models.Model):
    domain = models.ForeignKey(
        Domain,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="categories",
        help_text="Domaine principal utilisé pour les filtres du catalogue.",
    )
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    icon = models.CharField(
        max_length=50, default="BookOpen",
        help_text="Nom d'icône lucide-react (ex: Code2, Database, PenTool, Network)",
    )
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Level(models.TextChoices):
    BEGINNER = "beginner", "Débutant"
    INTERMEDIATE = "intermediate", "Intermédiaire"
    EXPERT = "expert", "Expert"


class StreamingStatus(models.TextChoices):
    PENDING = "pending", "En attente"
    PROCESSING = "processing", "Préparation en cours"
    READY = "ready", "Prêt"
    FAILED = "failed", "Échec"


class Course(models.Model):
    """Un cours = une PLAYLIST complète (plusieurs vidéos organisées en sections).
    On vend l'accès à l'ensemble du cours, pas à une vidéo isolée."""

    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="courses"
    )
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name="courses")
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    subtitle = models.CharField(max_length=255, blank=True)
    description = models.TextField()
    what_you_will_learn = models.JSONField(default=list, blank=True, help_text="Liste de points clés")
    requirements = models.JSONField(default=list, blank=True, help_text="Prérequis")
    target_audience = models.JSONField(default=list, blank=True)

    level = models.CharField(max_length=20, choices=Level.choices, default=Level.BEGINNER)
    language = models.CharField(max_length=50, default="Français")

    price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    is_free = models.BooleanField(default=False)
    discount_price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    thumbnail = models.ImageField(upload_to="courses/thumbnails/", blank=True, null=True)
    promo_video_url = models.URLField(blank=True)

    # Configuration du certificat de cours
    certificate_enabled = models.BooleanField(default=True)
    certificate_auto_issue = models.BooleanField(default=True)
    certificate_threshold_percent = models.PositiveSmallIntegerField(default=100)
    certificate_validity_months = models.PositiveIntegerField(null=True, blank=True)
    certificate_title = models.CharField(max_length=180, default="Certificat de réussite")
    certificate_subtitle = models.CharField(max_length=220, blank=True)
    certificate_description = models.TextField(blank=True)
    certificate_signatory_name = models.CharField(max_length=180, blank=True)
    certificate_signatory_title = models.CharField(max_length=180, blank=True)
    certificate_accent_color = models.CharField(max_length=20, default="#1f6f5c")
    certificate_number_prefix = models.CharField(max_length=30, default="LE-CERT")
    certificate_show_duration = models.BooleanField(default=True)
    certificate_show_instructor = models.BooleanField(default=True)
    certificate_show_completion_date = models.BooleanField(default=True)

    # Une vidéo hébergée par KalanPro n'est considérée terminée qu'après ce pourcentage
    # de visionnage réel cumulé. Le seuil est configurable par cours dans l'admin.
    video_completion_threshold_percent = models.PositiveSmallIntegerField(
        default=90, validators=[MinValueValidator(50), MaxValueValidator(100)]
    )

    published = models.BooleanField(default=False)
    featured = models.BooleanField(default=False)

    # champs calculés/cache, mis à jour via signaux
    total_duration_minutes = models.PositiveIntegerField(default=0)
    total_lessons = models.PositiveIntegerField(default=0)
    students_count = models.PositiveIntegerField(default=0)
    rating_avg = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    rating_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["published", "category"], name="catalog_cou_publish_85f2cc_idx"),
            models.Index(fields=["instructor", "published"], name="catalog_cou_instruc_115d51_idx"),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)
            slug = base
            i = 1
            while Course.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                i += 1
                slug = f"{base}-{i}"
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @property
    def total_hours(self):
        return round(self.total_duration_minutes / 60, 1)

    def refresh_aggregates(self):
        lessons = Lesson.objects.filter(section__course=self)
        self.total_lessons = lessons.count()
        self.total_duration_minutes = sum(l.duration_minutes for l in lessons)
        self.save(update_fields=["total_lessons", "total_duration_minutes"])


class Section(models.Model):
    """Un module/chapitre du cours (regroupe des leçons vidéo)."""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="sections")
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.course.title} · {self.title}"

    @property
    def duration_minutes(self):
        return sum(l.duration_minutes for l in self.lessons.all())


class Lesson(models.Model):
    """Une vidéo appartenant à la playlist d'un cours."""
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=200)
    video_url = models.URLField(blank=True, help_text="URL du fichier vidéo (stockage / CDN)")
    video_file = models.FileField(upload_to="courses/videos/", blank=True, null=True)
    duration_minutes = models.PositiveIntegerField(default=0)
    duration_seconds = models.PositiveIntegerField(default=0)
    order = models.PositiveIntegerField(default=0)
    is_preview = models.BooleanField(default=False, help_text="Vidéo gratuite consultable sans achat")
    description = models.TextField(blank=True)
    subtitles_file = models.FileField(upload_to="courses/subtitles/", blank=True, null=True, help_text="Sous-titres WebVTT (.vtt)")
    transcript = models.TextField(blank=True, help_text="Transcription texte de la leçon")
    # Streaming adaptatif généré en arrière-plan à partir du fichier source. Les chemins
    # pointent vers un paquet HLS versionné et ne sont jamais exposés directement au client.
    hls_master_path = models.CharField(max_length=500, blank=True)
    audio_hls_path = models.CharField(max_length=500, blank=True)
    streaming_status = models.CharField(max_length=20, choices=StreamingStatus.choices, default=StreamingStatus.PENDING)
    streaming_variants = models.JSONField(default=list, blank=True)
    streaming_error = models.TextField(blank=True)
    streaming_updated_at = models.DateTimeField(null=True, blank=True)

    # Téléchargement hors connexion contrôlé. La copie basse qualité est générée dans le
    # même paquet que le HLS, mais n'est exposée que lorsque l'instructeur/admin l'autorise.
    offline_download_allowed = models.BooleanField(default=False)
    offline_video_path = models.CharField(max_length=500, blank=True)
    offline_video_size_bytes = models.PositiveBigIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.section.course.title} · {self.title}"


class PDFResource(models.Model):
    """Un PDF rattaché à un cours (matériel additionnel inclus dans l'achat)."""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="pdf_resources")
    title = models.CharField(max_length=200)
    cover_image = models.ImageField(upload_to="courses/pdfs/covers/", blank=True, null=True)
    file = models.FileField(upload_to="courses/pdfs/")
    page_count = models.PositiveIntegerField(default=0)
    is_free_sample = models.BooleanField(default=False, help_text="Consultable sans achat (extrait gratuit)")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.course.title} · {self.title} (PDF)"


class PDFProduct(models.Model):
    """PDF vendu SEUL (catalogue indépendant des cours vidéo)."""
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pdf_products"
    )
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name="pdf_products")
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField()
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.BEGINNER)
    language = models.CharField(max_length=50, default="Français")

    price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    is_free = models.BooleanField(default=False)

    cover_image = models.ImageField(upload_to="pdfs/covers/", blank=True, null=True)
    file = models.FileField(upload_to="pdfs/files/")
    preview_file = models.FileField(upload_to="pdfs/previews/", blank=True, null=True)
    page_count = models.PositiveIntegerField(default=0)

    published = models.BooleanField(default=False)
    featured = models.BooleanField(default=False)

    downloads_count = models.PositiveIntegerField(default=0)
    rating_avg = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    rating_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["published", "category"], name="catalog_pdf_publish_8274ce_idx"),
            models.Index(fields=["instructor", "published"], name="catalog_pdf_instruc_fbc105_idx"),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)
            slug = base
            i = 1
            while PDFProduct.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                i += 1
                slug = f"{base}-{i}"
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} (PDF)"
