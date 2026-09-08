import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Carga de variables de entorno opcionales
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-tallerlogik-local-dev-key-change-in-prod')
DEBUG = os.environ.get('DEBUG', '1') == '1'

ALLOWED_HOSTS = [host.strip() for host in os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,0.0.0.0').split(',')]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Aplicaciones del proyecto
    'apps.core_auth',
    'apps.configuracion_base',
    'apps.cotizador',
    'apps.ordenes_trabajo',
    'apps.compras_gastos',
    'apps.rentabilidad_cobranzas',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # Middleware Multi-Tenant personalizado
    'apps.core_auth.middleware.TenantMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates' / 'html'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            'libraries': {
                'custom_filters': 'apps.core_auth.templatetags.custom_filters',
            },
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Configuración de Base de Datos (PostgreSQL por defecto, fallback local SQLite para testing)
DB_NAME = os.environ.get('DB_NAME', '')
if DB_NAME:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': DB_NAME,
            'USER': os.environ.get('DB_USER', 'taller_user'),
            'PASSWORD': os.environ.get('DB_PASSWORD', 'taller_password_secure'),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Modelo de Usuario Personalizado
AUTH_USER_MODEL = 'core_auth.Usuario'

# Validadores de Contraseña
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Seguridad de Sesión y Cookies
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
X_FRAME_OPTIONS = 'SAMEORIGIN'

LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/auth/dashboard/'
LOGOUT_REDIRECT_URL = '/auth/login/'

# Configuración de Logging con Filtro Multi-Tenant
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] [{levelname}] [T:{empresa_id}] [U:{usuario_email}] [{name}:{lineno}] - {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '[{asctime}] [{levelname}] - {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'filters': {
        'tenant_context_filter': {
            '()': 'apps.core_auth.log_filters.TenantContextFilter',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'archivo_actividad': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'sistema_actividad.log',
            'maxBytes': 1024 * 1024 * 15,  # 15 MB
            'backupCount': 10,
            'formatter': 'verbose',
            'filters': ['tenant_context_filter'],
            'encoding': 'utf-8',
        },
        'archivo_errores': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'sistema_errores.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
            'filters': ['tenant_context_filter'],
            'encoding': 'utf-8',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'archivo_errores'],
            'level': 'INFO',
            'propagate': False,
        },
        'saas_taller': {
            'handlers': ['console', 'archivo_actividad', 'archivo_errores'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# ==============================================================================
# CONFIGURACIÓN DE CELERY
# ==============================================================================
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Programación semanal de tareas (Celery Beat)
from celery.schedules import crontab
CELERY_BEAT_SCHEDULE = {
    'scraping-imperial-programado': {
        'task': 'apps.configuracion_base.tasks.tarea_scraping_imperial_programada',
        'schedule': crontab(day_of_week='0,4', hour=2, minute=0),  # Domingos (0) y Jueves (4) a las 02:00 AM
    },
}

