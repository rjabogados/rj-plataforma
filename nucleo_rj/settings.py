import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar las variables ocultas desde el archivo .env
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG') == 'True'

ALLOWED_HOSTS = ['*', '.ngrok-free.app', 'localhost', '127.0.0.1']

# Aquí agregamos la dirección que te dio Ngrok:
CSRF_TRUSTED_ORIGINS = [
    'https://why-unknown-wildfire.ngrok-free.dev', 
    'https://*.ngrok-free.app'
]

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
            ],
        },
    },
]

WSGI_APPLICATION = 'nucleo_rj.wsgi.application'

# Database
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
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'), # Aquí buscará tus diseños
]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

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

CORS_ALLOW_ALL_ORIGINS = True