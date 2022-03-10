

from ATIBAreport.setting_files.basesettings import *


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

DATABASE_ROUTERS = [
    'inventories.inventory_router.InventoryRouter',
    'accounts.accounts_router.AccountsRouter',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'defaultdb.sqlite3',
    },
    'atibadb': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'atibadb',
        'USER': 'atibapg',
        'PASSWORD': 'Gsxr1100!',
        'HOST': '127.0.0.1',
        'PORT': '5432',  # default port
    }

}
# print("database : "+str(DATABASES['default']['NAME']))


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static')
]

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_COOKIE_AGE = 1*60*60
# SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Settings for Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.FileHandler',
            'formatter': 'verbose',
            'filename': os.path.join(BASE_DIR, 'Log/ATIBAreport.log'),
        },
        'timer': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'formatter': 'timer',
            'filename': os.path.join(BASE_DIR, 'Log/ATIBAreportTimer.log'),
        },
        'memorytracer': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'formatter': 'timer',
            'filename': os.path.join(BASE_DIR, 'Log/ATIBAreportMemoryTracer.log'),
        }
    },
    'formatters': {
        'verbose': {
            'format': '[{levelname} - {name} - {asctime} - {funcName} - line {lineno} - process {process:d} - thread {thread:d}] : {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} - {name} - {asctime} - {message}',
            'style': '{',
        },
        'timer': {
            'format': '{name} - {asctime} - {funcName} - {message}',
            'style': '{',
        },
        'memorytracer': {
            'format': '{name} - {asctime} - {funcName} - {message}',
            'style': '{',
        }
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'views': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'commons': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'models': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'timer': {
            'handlers': ['console', 'timer'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'memorytracer': {
            'handlers': ['console', 'memorytracer'],
            'level': 'DEBUG',
            'propagate': False,
        }
    },
}



