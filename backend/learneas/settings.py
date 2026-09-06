"""
KalanPro — Configuration Django
Plateforme de vente de cours (playlists complètes) et de PDF (seuls ou inclus dans un cours).
"""
from pathlib import Path
from datetime import timedelta
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY", default="dev-secret-key-change-me")
DEBUG = config("DEBUG", default=True, cast=bool)
TEST_PAYMENTS_ENABLED = config("TEST_PAYMENTS_ENABLED", default=DEBUG, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="*", cast=Csv())

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # third party
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "channels",

    # local apps
    "apps.common",
    "apps.accounts",
    "apps.catalog",
    "apps.enrollments",
    "apps.payments",
    "apps.reviews",
    "apps.faq",
    "apps.chat",
    "apps.formations",
    "apps.notifications",
    "apps.support",
    "apps.projects",
    "apps.opportunities",
    "apps.assistant_ai.apps.AssistantAIConfig",
    "apps.discovery.apps.DiscoveryConfig",
    "apps.analytics.apps.AnalyticsConfig",
    "rest_framework_simplejwt.token_blacklist",
]

MIDDLEWARE = [
    "apps.common.middleware.request_id_middleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "learneas.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "learneas.wsgi.application"
ASGI_APPLICATION = "learneas.asgi.application"

import dj_database_url

DATABASE_URL = config("DATABASE_URL", default="")

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(DATABASE_URL, conn_max_age=600)
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": config("DB_ENGINE", default="django.db.backends.sqlite3"),
            "NAME": config("DB_NAME", default=BASE_DIR / "db.sqlite3"),
            "USER": config("DB_USER", default=""),
            "PASSWORD": config("DB_PASSWORD", default=""),
            "HOST": config("DB_HOST", default=""),
            "PORT": config("DB_PORT", default=""),
        }
    }

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Africa/Casablanca"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
USE_S3 = config("USE_S3", default=False, cast=bool)
REQUIRE_REMOTE_MEDIA = config("REQUIRE_REMOTE_MEDIA", default=not DEBUG, cast=bool)
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Limites médias configurables. Les vidéos de formation dépassent fréquemment 200 Mo ;
# les gros uploads basculent rapidement sur un fichier temporaire disque afin d'éviter
# de charger le processus Gunicorn en mémoire.
MAX_VIDEO_UPLOAD_MB = config("MAX_VIDEO_UPLOAD_MB", default=2048, cast=int)
MAX_PDF_UPLOAD_MB = config("MAX_PDF_UPLOAD_MB", default=100, cast=int)
MAX_IMAGE_UPLOAD_MB = config("MAX_IMAGE_UPLOAD_MB", default=15, cast=int)
MAX_IMAGE_DIMENSION = config("MAX_IMAGE_DIMENSION", default=12000, cast=int)
MAX_IMAGE_PIXELS = config("MAX_IMAGE_PIXELS", default=60_000_000, cast=int)
MAX_PROJECT_UPLOAD_MB = config("MAX_PROJECT_UPLOAD_MB", default=50, cast=int)
FILE_UPLOAD_MAX_MEMORY_SIZE = config("FILE_UPLOAD_MAX_MEMORY_SIZE", default=2 * 1024 * 1024, cast=int)

# Documents utilisateur : signature structurelle + antivirus ClamAV. En production, l'absence
# de scanner bloque uniquement les uploads documentaires concernés, pas le démarrage du site.
MALWARE_SCAN_ENABLED = config("MALWARE_SCAN_ENABLED", default=False, cast=bool)
MALWARE_SCAN_REQUIRED = config("MALWARE_SCAN_REQUIRED", default=not DEBUG, cast=bool)
CLAMAV_HOST = config("CLAMAV_HOST", default="")
CLAMAV_PORT = config("CLAMAV_PORT", default=3310, cast=int)
CLAMAV_TIMEOUT_SECONDS = config("CLAMAV_TIMEOUT_SECONDS", default=30, cast=int)

PRIVATE_MEDIA_TOKEN_MAX_AGE = config("PRIVATE_MEDIA_TOKEN_MAX_AGE", default=15 * 60, cast=int)
# Les segments d'une longue vidéo HLS doivent rester lisibles jusqu'à la fin de la lecture.
# Ils ont donc une fenêtre distincte des CV/PDF/fichiers privés classiques.
HLS_MEDIA_TOKEN_MAX_AGE = config("HLS_MEDIA_TOKEN_MAX_AGE", default=6 * 60 * 60, cast=int)

# En production S3/R2, les vidéos volumineuses sont envoyées directement au bucket par
# multipart upload. Django ne signe que les blocs puis enregistre l'objet final : Gunicorn
# ne transporte plus jusqu'à 2 Go par requête. En local (USE_S3=False), le formulaire
# conserve automatiquement l'upload HTTP classique.
DIRECT_MEDIA_UPLOADS_ENABLED = config("DIRECT_MEDIA_UPLOADS_ENABLED", default=USE_S3, cast=bool)
DIRECT_UPLOAD_PART_SIZE_MB = config("DIRECT_UPLOAD_PART_SIZE_MB", default=16, cast=int)
DIRECT_UPLOAD_URL_TTL_SECONDS = config("DIRECT_UPLOAD_URL_TTL_SECONDS", default=3600, cast=int)

# Normalisation vidéo navigateur : évite les MP4/MOV techniquement valides mais illisibles
# côté HTML5 (HEVC/H.265, H.264 10-bit, audio incompatible, etc.). ffmpeg est déjà
# installé dans l'image backend. Les uploads compatibles H.264/AAC ne sont pas réencodés.
VIDEO_NORMALIZATION_ENABLED = config("VIDEO_NORMALIZATION_ENABLED", default=True, cast=bool)
VIDEO_PROBE_TIMEOUT_SECONDS = config("VIDEO_PROBE_TIMEOUT_SECONDS", default=120, cast=int)
VIDEO_TRANSCODE_TIMEOUT_SECONDS = config("VIDEO_TRANSCODE_TIMEOUT_SECONDS", default=3600, cast=int)
VIDEO_TRANSCODE_PRESET = config("VIDEO_TRANSCODE_PRESET", default="veryfast")
VIDEO_TRANSCODE_CRF = config("VIDEO_TRANSCODE_CRF", default=22, cast=int)

# Streaming HLS adaptatif : 240p/360p/480p/720p + piste audio seule très faible débit.
# Le transcodage est asynchrone via Celery pour ne jamais bloquer les requêtes HTTP.
HLS_STREAMING_ENABLED = config("HLS_STREAMING_ENABLED", default=True, cast=bool)
HLS_MAX_HEIGHT = config("HLS_MAX_HEIGHT", default=720, cast=int)
HLS_SEGMENT_SECONDS = config("HLS_SEGMENT_SECONDS", default=6, cast=int)
HLS_TRANSCODE_TIMEOUT_SECONDS = config("HLS_TRANSCODE_TIMEOUT_SECONDS", default=7200, cast=int)
HLS_TRANSCODE_PRESET = config("HLS_TRANSCODE_PRESET", default="veryfast")
HLS_AUDIO_ONLY_BITRATE = config("HLS_AUDIO_ONLY_BITRATE", default="48k")
HLS_DATA_SAVER_MAX_HEIGHT = config("HLS_DATA_SAVER_MAX_HEIGHT", default=360, cast=int)
HLS_SEGMENT_CACHE_SECONDS = config("HLS_SEGMENT_CACHE_SECONDS", default=600, cast=int)

# Railway utilise un disque éphémère par défaut : activez USE_S3 avec un bucket S3-compatible
# (AWS, Cloudflare R2, Backblaze, MinIO, etc.) pour conserver durablement les médias.
if USE_S3:
    AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = config("AWS_S3_REGION_NAME", default=None)
    AWS_S3_ENDPOINT_URL = config("AWS_S3_ENDPOINT_URL", default=None)
    AWS_S3_CUSTOM_DOMAIN = config("AWS_S3_CUSTOM_DOMAIN", default=None)
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = True
    AWS_QUERYSTRING_EXPIRE = 300
    AWS_S3_FILE_OVERWRITE = False
    AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "private, no-store"}
    STORAGES["default"] = {"BACKEND": "storages.backends.s3.S3Storage"}
    if AWS_S3_CUSTOM_DOMAIN:
        MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN.rstrip('/')}/"
    elif AWS_S3_ENDPOINT_URL:
        MEDIA_URL = f"{AWS_S3_ENDPOINT_URL.rstrip('/')}/{AWS_STORAGE_BUCKET_NAME}/"
    else:
        MEDIA_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/"
elif not DEBUG and REQUIRE_REMOTE_MEDIA:
    raise RuntimeError("Stockage média distant requis : configurez USE_S3=True et les variables AWS/S3.")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# DRF / JWT / CORS / API docs
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    # L’API KalanPro est authentifiée exclusivement par JWT.
    # Ne pas activer SessionAuthentication ici : une session Django (par exemple après
    # connexion à /admin/) ferait appliquer un contrôle CSRF aux endpoints publics
    # /api/auth/login/ et /api/auth/register/, alors que le frontend Next.js utilise JWT.
    # L’admin Django conserve sa propre authentification par session et sa protection CSRF.
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.accounts.authentication.PasswordBoundJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 12,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Réserve ?format= aux endpoints métier (ex. export PDF/DOCX) au lieu du renderer DRF.
    "URL_FORMAT_OVERRIDE": None,
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        # Les endpoints publics du catalogue chargent plusieurs ressources par page.
        # En développement on garde une protection élevée sans gêner les tests manuels ;
        # en production les valeurs restent bornées et peuvent être ajustées par variables
        # d'environnement. Les opérations sensibles conservent leurs throttles dédiés.
        "anon": config(
            "ANON_THROTTLE_RATE",
            default="10000/hour" if DEBUG else "1200/hour",
        ),
        "user": config(
            "USER_THROTTLE_RATE",
            default="30000/hour" if DEBUG else "6000/hour",
        ),
        "auth": "10/min",
        "token_refresh": "60/min",
        "password_reset": "5/hour",
        "checkout": "20/hour",
        "media": config("MEDIA_THROTTLE_RATE", default="5000/hour" if DEBUG else "2000/hour"),
        "live": "12000/hour",
        "admin_test": "30/hour",
        "webhook": "3000/hour",
        "certificate_verify": config("CERTIFICATE_VERIFY_THROTTLE_RATE", default="300/hour"),
        "client_telemetry": config("CLIENT_TELEMETRY_THROTTLE_RATE", default="60/hour"),
        "product_analytics": config("PRODUCT_ANALYTICS_THROTTLE_RATE", default="500/hour" if DEBUG else "300/hour"),
        "ai": config("AI_THROTTLE_RATE", default="60/min" if DEBUG else "30/min"),
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    # Le refresh est HttpOnly et partagé par tous les onglets. Ne pas le faire tourner à chaque
    # requête évite qu'un second onglet invalide le cookie qu'un premier vient de remplacer.
    # Logout et changement de mot de passe le blacklistent explicitement.
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "UPDATE_LAST_LOGIN": True,
}

# Le refresh JWT n'est jamais exposé à JavaScript : il vit uniquement dans un cookie HttpOnly.
# En production, le frontend doit idéalement appeler l'API via le proxy same-origin /api (Vercel
# -> Railway) afin d'éviter la dépendance aux cookies tiers sur Safari/Chrome mobile.
AUTH_REFRESH_COOKIE_NAME = config("AUTH_REFRESH_COOKIE_NAME", default="learneas_refresh")
AUTH_REFRESH_COOKIE_PATH = config("AUTH_REFRESH_COOKIE_PATH", default="/api/auth/")
AUTH_REFRESH_COOKIE_DOMAIN = config("AUTH_REFRESH_COOKIE_DOMAIN", default="").strip() or None
AUTH_REFRESH_COOKIE_SECURE = config("AUTH_REFRESH_COOKIE_SECURE", default=not DEBUG, cast=bool)
AUTH_REFRESH_COOKIE_SAMESITE = config("AUTH_REFRESH_COOKIE_SAMESITE", default="Lax")
AUTH_REFRESH_COOKIE_MAX_AGE = config("AUTH_REFRESH_COOKIE_MAX_AGE", default=7 * 24 * 60 * 60, cast=int)
if AUTH_REFRESH_COOKIE_SAMESITE not in {"Lax", "Strict", "None"}:
    raise RuntimeError("AUTH_REFRESH_COOKIE_SAMESITE doit valoir Lax, Strict ou None.")
if AUTH_REFRESH_COOKIE_SAMESITE == "None" and not AUTH_REFRESH_COOKIE_SECURE:
    raise RuntimeError("SameSite=None exige AUTH_REFRESH_COOKIE_SECURE=True.")

CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost,http://127.0.0.1,http://localhost:3000,http://127.0.0.1:3000",
    cast=Csv(),
)
# Nécessaire pour que les réponses login/refresh puissent poser/renvoyer le cookie HttpOnly
# lorsque l'API est appelée depuis une origine frontend explicitement autorisée.
CORS_ALLOW_CREDENTIALS = True

SPECTACULAR_SETTINGS = {
    "TITLE": "KalanPro API",
    "DESCRIPTION": "API de la plateforme de formation en ligne KalanPro",
    "VERSION": "1.0.0",
}

STRIPE_SECRET_KEY = config("STRIPE_SECRET_KEY", default="")
STRIPE_TEST_SECRET_KEY = config("STRIPE_TEST_SECRET_KEY", default="")
STRIPE_PUBLISHABLE_KEY = config("STRIPE_PUBLISHABLE_KEY", default="")
STRIPE_WEBHOOK_SECRET = config("STRIPE_WEBHOOK_SECRET", default="")
STRIPE_TEST_WEBHOOK_SECRET = config("STRIPE_TEST_WEBHOOK_SECRET", default="")
YOUCANPAY_ACCESS_TOKEN = config("YOUCANPAY_ACCESS_TOKEN", default="")
YOUCANPAY_API_BASE = config("YOUCANPAY_API_BASE", default="https://youcanpay.com/api/v2")
# Le sandbox YouCan Pay est entièrement configurable. Les jetons sandbox et production sont
# volontairement séparés : une passerelle en mode test ne réutilise jamais un secret live.
YOUCANPAY_SANDBOX_ACCESS_TOKEN = config("YOUCANPAY_SANDBOX_ACCESS_TOKEN", default="")
YOUCANPAY_SANDBOX_API_BASE = config("YOUCANPAY_SANDBOX_API_BASE", default="")
GENIUSPAY_API_KEY = config("GENIUSPAY_API_KEY", default="")
GENIUSPAY_API_SECRET = config("GENIUSPAY_API_SECRET", default="")
GENIUSPAY_WEBHOOK_SECRET = config("GENIUSPAY_WEBHOOK_SECRET", default="")
GENIUSPAY_API_BASE = config("GENIUSPAY_API_BASE", default="https://geniuspay.ci/api/v1/merchant")
GENIUSPAY_SANDBOX_API_KEY = config("GENIUSPAY_SANDBOX_API_KEY", default="")
GENIUSPAY_SANDBOX_API_SECRET = config("GENIUSPAY_SANDBOX_API_SECRET", default="")
GENIUSPAY_SANDBOX_WEBHOOK_SECRET = config("GENIUSPAY_SANDBOX_WEBHOOK_SECRET", default="")
GENIUSPAY_SANDBOX_API_BASE = config("GENIUSPAY_SANDBOX_API_BASE", default="")

# CinetPay — Mobile Money Afrique francophone. Les identifiants sandbox et production
# sont volontairement séparés afin d'éviter toute charge réelle pendant les tests.
CINETPAY_API_KEY = config("CINETPAY_API_KEY", default="")
CINETPAY_SITE_ID = config("CINETPAY_SITE_ID", default="")
CINETPAY_SECRET_KEY = config("CINETPAY_SECRET_KEY", default="")
CINETPAY_API_BASE = config("CINETPAY_API_BASE", default="https://api-checkout.cinetpay.com/v2")
CINETPAY_SANDBOX_API_KEY = config("CINETPAY_SANDBOX_API_KEY", default="")
CINETPAY_SANDBOX_SITE_ID = config("CINETPAY_SANDBOX_SITE_ID", default="")
CINETPAY_SANDBOX_SECRET_KEY = config("CINETPAY_SANDBOX_SECRET_KEY", default="")
CINETPAY_SANDBOX_API_BASE = config("CINETPAY_SANDBOX_API_BASE", default="")
PAYMENT_CURRENCY = config("PAYMENT_CURRENCY", default="EUR")

# Répartition des ventes instructeurs / plateforme
PLATFORM_COMMISSION_PERCENT = config("PLATFORM_COMMISSION_PERCENT", default=15, cast=int)
MINIMUM_PAYOUT_AMOUNT = config("MINIMUM_PAYOUT_AMOUNT", default=10, cast=int)
FRONTEND_URL = config("FRONTEND_URL", default="http://localhost:3000")
# URL publique du backend, indispensable aux webhooks de paiement (ex. Railway).
# En local derrière Nginx, FRONTEND_URL convient comme valeur de repli car /api y est proxyfié.
BACKEND_PUBLIC_URL = config("BACKEND_PUBLIC_URL", default=FRONTEND_URL)

# ---------------------------------------------------------------------------
# WhatsApp Cloud API (Meta) — messages transactionnels avec consentement explicite.
# WHATSAPP_DRY_RUN=True en local journalise les envois sans appeler Meta.
# ---------------------------------------------------------------------------
WHATSAPP_ENABLED = config("WHATSAPP_ENABLED", default=False, cast=bool)
WHATSAPP_DRY_RUN = config("WHATSAPP_DRY_RUN", default=True, cast=bool)
WHATSAPP_GRAPH_API_VERSION = config("WHATSAPP_GRAPH_API_VERSION", default="v25.0")
WHATSAPP_PHONE_NUMBER_ID = config("WHATSAPP_PHONE_NUMBER_ID", default="")
WHATSAPP_ACCESS_TOKEN = config("WHATSAPP_ACCESS_TOKEN", default="")
WHATSAPP_VERIFY_TOKEN = config("WHATSAPP_VERIFY_TOKEN", default="")
WHATSAPP_APP_SECRET = config("WHATSAPP_APP_SECRET", default="")
WHATSAPP_HTTP_TIMEOUT = config("WHATSAPP_HTTP_TIMEOUT", default=15, cast=int)

# ---------------------------------------------------------------------------
# Email — console en développement (le lien de réinitialisation s'affiche dans les
# logs du conteneur backend), SMTP réel en production via variables d'environnement.
# ---------------------------------------------------------------------------
EMAIL_BACKEND = config(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend" if DEBUG
    else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = config("EMAIL_HOST", default="")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="KalanPro <no-reply@kalanpro.com>")

# Resend Email API — canal transactionnel principal. La clé API ne doit jamais être
# stockée en base ni exposée au frontend. RESEND_DRY_RUN=True en local permet de
# valider tout le workflow sans appeler l'API externe.
RESEND_ENABLED = config("RESEND_ENABLED", default=False, cast=bool)
RESEND_DRY_RUN = config("RESEND_DRY_RUN", default=True, cast=bool)
RESEND_API_KEY = config("RESEND_API_KEY", default="")
RESEND_API_BASE = config("RESEND_API_BASE", default="https://api.resend.com")
RESEND_HTTP_TIMEOUT = config("RESEND_HTTP_TIMEOUT", default=15, cast=int)

# ---------------------------------------------------------------------------
# Redis / Celery (emails asynchrones, tâches planifiées) — service "redis" du docker-compose
# ---------------------------------------------------------------------------
REDIS_URL = config("REDIS_URL", default="redis://localhost:6379/0")
REALTIME_TICKET_MAX_AGE_SECONDS = config("REALTIME_TICKET_MAX_AGE_SECONDS", default=60, cast=int)
RTC_STUN_URL = config("RTC_STUN_URL", default="stun:stun.l.google.com:19302")
RTC_TURN_URL = config("RTC_TURN_URL", default="")
RTC_TURN_SECRET = config("RTC_TURN_SECRET", default="")
RTC_TURN_TTL_SECONDS = config("RTC_TURN_TTL_SECONDS", default=3600, cast=int)
RTC_TURN_USERNAME = config("RTC_TURN_USERNAME", default="")
RTC_TURN_CREDENTIAL = config("RTC_TURN_CREDENTIAL", default="")
REALTIME_ALLOWED_ORIGINS = config(
    "REALTIME_ALLOWED_ORIGINS",
    default=",".join(CORS_ALLOWED_ORIGINS) if CORS_ALLOWED_ORIGINS else "http://localhost:3000",
    cast=Csv(),
)
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
            "capacity": config("REALTIME_CHANNEL_CAPACITY", default=500, cast=int),
            "expiry": config("REALTIME_CHANNEL_EXPIRY_SECONDS", default=60, cast=int),
        },
    }
}
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "TIMEOUT": 300,
    }
}
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ROUTES = {
    # ffprobe/ffmpeg/HLS : file dédiée, consommée par un worker média séparé.
    "apps.catalog.tasks.*": {"queue": "media"},
    # WhatsApp/rappels : ne doivent jamais attendre derrière un transcodage de plusieurs heures.
    "apps.notifications.tasks.*": {"queue": "notifications"},
    "apps.enrollments.tasks.*": {"queue": "default"},
    "apps.assistant_ai.tasks.*": {"queue": "default"},
}
# Assistant IA — la clé reste uniquement dans l'environnement. Le backend utilise une
# API chat compatible ; AI_DRY_RUN permet de tester toute la Phase 1 sans consommer de crédits.
AI_API_KEY = config("AI_API_KEY", default="")
AI_API_BASE = config("AI_API_BASE", default="https://api.openai.com/v1")
AI_CHAT_MODEL = config("AI_CHAT_MODEL", default="")
AI_PROVIDER_NAME = config("AI_PROVIDER_NAME", default="Compatible API")
AI_HTTP_TIMEOUT = config("AI_HTTP_TIMEOUT", default=60, cast=int)
AI_DRY_RUN = config("AI_DRY_RUN", default=DEBUG, cast=bool)
AI_INDEX_ASYNC = config("AI_INDEX_ASYNC", default=not DEBUG, cast=bool)
AI_VISION_ENABLED = config("AI_VISION_ENABLED", default=False, cast=bool)

PAYMENT_RECONCILIATION_MIN_AGE_SECONDS = config("PAYMENT_RECONCILIATION_MIN_AGE_SECONDS", default=120, cast=int)
PAYMENT_RECONCILIATION_BATCH_SIZE = config("PAYMENT_RECONCILIATION_BATCH_SIZE", default=100, cast=int)
PAYMENT_ORDER_EXPIRY_HOURS = config("PAYMENT_ORDER_EXPIRY_HOURS", default=24, cast=int)
PAYMENT_STALE_BATCH_SIZE = config("PAYMENT_STALE_BATCH_SIZE", default=200, cast=int)
COHORT_WAITLIST_OFFER_HOURS = config("COHORT_WAITLIST_OFFER_HOURS", default=24, cast=int)

ANALYTICS_RETENTION_DAYS = config("ANALYTICS_RETENTION_DAYS", default=395, cast=int)

CELERY_BEAT_SCHEDULE = {
    "payment-reconciliation-every-5-minutes": {
        "task": "apps.payments.tasks.reconcile_pending_payments",
        "schedule": 300.0,
    },
    "payment-stale-review-hourly": {
        "task": "apps.payments.tasks.flag_stale_pending_payments",
        "schedule": 3600.0,
    },
    "whatsapp-live-reminders-every-5-minutes": {
        "task": "apps.notifications.tasks.dispatch_whatsapp_live_reminders",
        "schedule": 300.0,
    },
    "whatsapp-inactivity-reminders-daily": {
        "task": "apps.notifications.tasks.dispatch_whatsapp_inactivity_reminders",
        "schedule": 86400.0,
    },
    "recruitment-interview-reminders-every-5-minutes": {
        "task": "apps.notifications.tasks.dispatch_recruitment_interview_reminders",
        "schedule": 300.0,
    },
    "saved-talent-search-alerts-hourly": {
        "task": "apps.notifications.tasks.dispatch_saved_talent_search_alerts",
        "schedule": 3600.0,
    },
    "certificate-expiration-hourly": {
        "task": "apps.enrollments.tasks.expire_certificates",
        "schedule": 3600.0,
    },
    "cohort-waitlist-refresh-every-15-minutes": {
        "task": "apps.formations.tasks.refresh_cohort_waitlists",
        "schedule": 900.0,
    },
    "mentorship-recurring-slots-every-12-hours": {
        "task": "apps.formations.tasks.generate_recurring_mentorship_slots",
        "schedule": 43200.0,
    },
    "analytics-product-events-retention-daily": {
        "task": "apps.analytics.tasks.purge_old_product_events",
        "schedule": 86400.0,
    },
}




# ---------------------------------------------------------------------------
# Logs / observabilité
# ---------------------------------------------------------------------------
LOG_LEVEL = config("LOG_LEVEL", default="INFO").upper()
LOG_FORMAT = config("LOG_FORMAT", default="console" if DEBUG else "json").lower()
if LOG_FORMAT not in {"console", "json"}:
    raise RuntimeError("LOG_FORMAT doit valoir 'console' ou 'json'.")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_context": {"()": "apps.common.logging.RequestContextFilter"},
    },
    "formatters": {
        "console": {
            "format": "%(asctime)s %(levelname)s %(name)s [request_id=%(request_id)s] %(message)s",
        },
        "json": {"()": "apps.common.logging.JsonFormatter"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "filters": ["request_context"],
            "formatter": LOG_FORMAT,
        },
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django.server": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "django.request": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "kalanpro.request": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}


# ---------------------------------------------------------------------------
# Sécurité production — activée uniquement si DEBUG=False.
# IMPORTANT : les cookies "Secure" (SESSION_COOKIE_SECURE / CSRF_COOKIE_SECURE) ne doivent être
# activés QUE si le site est réellement servi en HTTPS. Sinon le navigateur refuse de renvoyer
# ces cookies, et TOUT formulaire (dont la connexion à /admin/) échoue avec une erreur CSRF 403,
# même avec des identifiants corrects. Par défaut (installation Docker locale en http://localhost),
# USE_HTTPS reste à False. Passez USE_HTTPS=True dans votre .env uniquement si nginx/un reverse
# proxy termine bien du HTTPS devant l'application.
# ---------------------------------------------------------------------------
if not DEBUG:
    USE_HTTPS = config("USE_HTTPS", default=False, cast=bool)
    SECURE_SSL_REDIRECT = USE_HTTPS
    SESSION_COOKIE_SECURE = USE_HTTPS
    CSRF_COOKIE_SECURE = USE_HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    if USE_HTTPS:
        SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=31536000, cast=int)
        SECURE_HSTS_INCLUDE_SUBDOMAINS = config("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False, cast=bool)
        SECURE_HSTS_PRELOAD = config("SECURE_HSTS_PRELOAD", default=False, cast=bool)
    CSRF_TRUSTED_ORIGINS = config(
        "CSRF_TRUSTED_ORIGINS",
        default="http://localhost,http://127.0.0.1",
        cast=Csv(),
    )


# Garde-fous de déploiement : refuser les secrets/hosts de développement en production.
if not DEBUG:
    if SECRET_KEY in {"dev-secret-key-change-me", "change-me-in-production"} or len(SECRET_KEY) < 32:
        raise RuntimeError("SECRET_KEY invalide pour la production.")
    if "*" in ALLOWED_HOSTS:
        raise RuntimeError("ALLOWED_HOSTS='*' est interdit en production.")
    if not AUTH_REFRESH_COOKIE_SECURE:
        raise RuntimeError("AUTH_REFRESH_COOKIE_SECURE=False est interdit en production.")
    if TEST_PAYMENTS_ENABLED:
        raise RuntimeError("TEST_PAYMENTS_ENABLED=True est interdit en production.")
    if config("SEED_DEMO", default=False, cast=bool):
        raise RuntimeError("SEED_DEMO=True est interdit en production.")
    if not CORS_ALLOWED_ORIGINS or any(str(origin).strip() == "*" for origin in CORS_ALLOWED_ORIGINS):
        raise RuntimeError("CORS_ALLOWED_ORIGINS doit contenir uniquement des origines explicites en production.")
    if USE_HTTPS:
        for label, value in (("FRONTEND_URL", FRONTEND_URL), ("BACKEND_PUBLIC_URL", BACKEND_PUBLIC_URL)):
            if not str(value).lower().startswith("https://"):
                raise RuntimeError(f"{label} doit utiliser https:// lorsque USE_HTTPS=True.")
        for label, origins in (
            ("CORS_ALLOWED_ORIGINS", CORS_ALLOWED_ORIGINS),
            ("REALTIME_ALLOWED_ORIGINS", REALTIME_ALLOWED_ORIGINS),
            ("CSRF_TRUSTED_ORIGINS", CSRF_TRUSTED_ORIGINS),
        ):
            if any(not str(origin).lower().startswith("https://") for origin in origins):
                raise RuntimeError(f"{label} doit contenir uniquement des origines https:// lorsque USE_HTTPS=True.")
    if not REALTIME_ALLOWED_ORIGINS or any(
        str(origin).strip() in {"*", "http://*", "https://*"} for origin in REALTIME_ALLOWED_ORIGINS
    ):
        raise RuntimeError("REALTIME_ALLOWED_ORIGINS doit contenir uniquement des origines explicites en production.")
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
    X_FRAME_OPTIONS = "DENY"

OFFLINE_VIDEO_ENABLED = config("OFFLINE_VIDEO_ENABLED", default=True, cast=bool)
OFFLINE_VIDEO_MAX_HEIGHT = config("OFFLINE_VIDEO_MAX_HEIGHT", default=360, cast=int)
OFFLINE_VIDEO_MAX_MB = config("OFFLINE_VIDEO_MAX_MB", default=250, cast=int)
OFFLINE_PROGRESS_TOKEN_MAX_AGE = config(
    "OFFLINE_PROGRESS_TOKEN_MAX_AGE",
    default=30 * 24 * 3600,
    cast=int,
)
