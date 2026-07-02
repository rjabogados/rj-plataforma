import os
import dj_database_url
from pathlib import Path
from dotenv import load_dotenv

# Cargar las variables ocultas desde el archivo .env
load_dotenv(override=True)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 't', 'yes', 'on'}


def env_list(name, default=None):
    value = os.environ.get(name)
    if value is None:
        return list(default or [])
    return [item.strip() for item in value.split(',') if item.strip()]

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-dev-only-change-me')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env_bool('DEBUG', default=False)

ALLOWED_HOSTS = env_list(
    'ALLOWED_HOSTS',
    default=['127.0.0.1', 'localhost', 'rj-plataforma.onrender.com', 'www.rj-plataforma.onrender.com', 'rjplataforma.up.railway.app'],
)

CSRF_TRUSTED_ORIGINS = env_list(
    'CSRF_TRUSTED_ORIGINS',
    default=['https://rj-plataforma.onrender.com', 'https://www.rj-plataforma.onrender.com', 'https://rjplataforma.up.railway.app'],
)

# Application definition
INSTALLED_APPS = [
    'intranet',    
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'nucleo_rj.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'intranet.context_processors.notificaciones_usuario',
            ],
        },
    },
]

WSGI_APPLICATION = 'nucleo_rj.wsgi.application'

# ==========================================
# CONFIGURACIÓN HÍBRIDA DE BASE DE DATOS
# ==========================================
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    # 1. EN LA NUBE (Render - PostgreSQL)
    DATABASES = {
        'default': dj_database_url.config(default=DATABASE_URL, conn_max_age=600)
    }
else:
    # 2. EN TU COMPUTADORA (Local - SQLite3)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'es-pe'
TIME_ZONE = 'America/Lima'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static')
]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# Configuraciones de Archivos Subidos (PDFs, Imágenes)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Rutas de redirección para el Login
LOGIN_URL = 'login'  
LOGIN_REDIRECT_URL = 'inicio' 
LOGOUT_REDIRECT_URL = 'login'

# ==========================================
# CONFIGURACIÓN GOOGLE SHEETS
# ==========================================
GOOGLE_SHEETS_CONFIG = {
    'SHEET_ID': os.environ.get('GOOGLE_SHEET_ID'),
    'RANGE_NAME': 'Respuestas!A:Z', 
}

# ==========================================
# CONFIGURACIÓN DE CORREOS (RJ TALENT)
# ==========================================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
# Credenciales leídas de forma segura desde el archivo .env
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER') 
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD') 
DEFAULT_FROM_EMAIL = f"RJ Talent <{os.environ.get('EMAIL_HOST_USER')}>"

# Orígenes CORS permitidos (NO todos)
CORS_ALLOWED_ORIGINS = [
    "https://rj-plataforma.onrender.com",
    "https://www.rj-plataforma.onrender.com",
    "https://rjplataforma.up.railway.app",
]

# NUNCA usar CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_ALL_ORIGINS = False

# Headers CORS seguros
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

# Permitir iframes del mismo dominio (Para el visor de PDFs de la Academia LMS)
X_FRAME_OPTIONS = 'SAMEORIGIN'

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'

if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', default=True)
    SESSION_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_SAMESITE = 'Lax'

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")