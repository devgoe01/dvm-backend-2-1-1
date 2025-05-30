from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv()
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


SECRET_KEY = os.environ.get('SECRET_KEY')
DEBUG = os.environ.get("DEBUG") == "True"



ALLOWED_HOSTS=os.environ.get("DJANGO_ALLOWED_HOSTS").split(" ")
CSRF_TRUSTED_ORIGINS = os.environ.get("CSRF_TRUSTED_ORIGINS").split(" ")
#CSRF_TRUSTED_ORIGINS = ['http://127.0.0.1:1337/','http://127.0.0.1:8000/','http://localhost:8000/','http://localhost:1337/','http://127.0.0.1:1337/admin/']
# Application definition

INSTALLED_APPS = [
    'users.apps.UsersConfig',
    'bus.apps.BusConfig',
    'crispy_forms',
    'crispy_bootstrap4',
    'allauth',
    'django_extensions',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]


'''LEAFLET_CONFIG = {
    'DEFAULT_CENTER': (0, 0),
    'DEFAULT_ZOOM': 13,
}
'''
# myproject/settings.py

'''# set the celery broker url
CELERY_BROKER_URL = 'redis://localhost:6379/0'

# set the celery result backend
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

# set the celery timezone
CELERY_TIMEZONE = 'UTC'
'''
'''SOCIALACCOUNT_PROVIDERS = {
    "google":{
        "SCOPE":[
            "profile",
            "email"
        ],
        "AUTH_PARAMS" : {"access_type" : "online"},
        'APP': {
            'client_id': os.environ.get('GOOGLE_CLIENT_ID'),
            'secret': os.environ.get('GOOGLE_CLIENT_SECRET'),
            'key': '',
#           'redirect_uris': ['http://127.0.0.1:1337/accounts/google/login/callback/'],
#            'callback_url': 'http://127.0.0.1:1337/accounts/google/login/callback/'
        }
    }
}

'''

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.environ.get('GOOGLE_CLIENT_ID')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
#SOCIAL_AUTH_GOOGLE_OAUTH2_REDIRECT_URI = 'http://127.0.0.1:1337/accounts/google/login/callback/'
SITE_ID = 1
SOCIALACCOUNT_LOGIN_ON_GET = True
#SOCIALACCOUNT_ADAPTER = 'users.adapters.CustomSocialAccountAdapter'

SOCIALACCOUNT_PROVIDERS = {
    "google":{
        "SCOPE":[
            "profile",
            "email"
        ],
        "AUTH_PARAMS" : {"access_type" : "online"},
    }
}


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = 'bus_service.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates'),os.path.join(BASE_DIR, 'bus', 'templates'),os.path.join(BASE_DIR, 'users', 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
AUTHENTICATION_BACKENDS = ['allauth.account.auth_backends.AuthenticationBackend']


WSGI_APPLICATION = 'bus_service.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases
#GDAL_LIBRARY_PATH = r"C:\OSGeo4W64\bin\gdal310.dll"
DATABASES = {
    "default": {
        "ENGINE": os.environ.get("SQL_ENGINE", "django.db.backends.sqlite3"),
        "NAME": os.environ.get("POSTGRES_DB", os.path.join(BASE_DIR, "db.sqlite3")),
        "USER": os.environ.get("POSTGRES_USER"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD"),
        "HOST": os.environ.get("SQL_HOST"),
        "PORT": os.environ.get("SQL_PORT"),
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.ScryptPasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'
USE_TZ = True
TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# settings.py
#SOCIAL_AUTH_GOOGLE_OAUTH2_REDIRECT_URI = 'http://127.0.0.1:1337/accounts/google/login/callback/'

'''#SOCIAL_AUTH_GOOGLE_OAUTH2_REDIRECT_URL = 'http://web/accounts/google/login/callback/'
SOCIAL_AUTH_GOOGLE_OAUTH2_CALLBACK_URL = 'http://web/accounts/google/login/callback/'''
#USE_X_FORWARDED_HOST = True
#SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'http')
#OAUTH_URL = 'http://127.0.0.1:8000'
#
# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/
# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'bus','static'),
]

STATIC_ROOT = os.path.join(BASE_DIR, 'static')


CRISPY_TEMPLATE_PACK = 'bootstrap4'

LOGIN_REDIRECT_URL = '/dashboard/'
LOGIN_URL = 'login'
LOGOUT_REDIRECT_URL = 'project-home'
AUTH_USER_MODEL='bus.User'
SOCIALACCOUNT_AUTO_SIGNUP = True
ACCOUNT_UNIQUE_EMAIL = True
SOCIALACCOUNT_ADAPTER = 'users.adapters.MySocialAccountAdapter' 
SOCIALACCOUNT_LOGIN_ON_GET = True

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'madhugoe05@gmail.com'
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bus_service.settings')
'''SOCIAL_ACCOUNT_LOGIN_ON_GET = True
CORS_ALLOWED_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://web:8000",
    "http://web:1337",
    "http://web",
    "http://127.0.0.1:1337",
    "http://localhost:1337",
]
INTERNAL_IPS = [
    '127.0.0.1',
    'localhost',
]'''