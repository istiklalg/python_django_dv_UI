
from ATIBAreport.setting_files.basesettings import *

# SECURITY WARNING: don't run with debug turned on in production!
from ATIBAreport.setting_files.passes import *

DEBUG = False

ALLOWED_HOSTS = ['*']

# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

DATABASE_ROUTERS = [
    'inventories.inventory_router.InventoryRouter',
    'accounts.accounts_router.AccountsRouter',
]

DATABASES = {

    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        # 'NAME': BASE_DIR / 'db.sqlite3',
        'NAME': '/usr/local/atiba/AtibaReporting/defaultdb.sqlite3',
    },

    'atibadb': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': postgres_production_dbName,
        'USER': postgres_production_user,
        'PASSWORD': postgres_production_pass,
        'HOST': postgres_production_host,
        'PORT': '5432',  # default port
    }
}

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/
# STATIC_URL = '/static/'
#
# STATICFILES_DIRS = [
#     os.path.join(BASE_DIR, 'static')
# ]

# STATIC_ROOT = os.path.join('/static/')
# STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATIC_ROOT = '/usr/local/atiba/AtibaReporting/static'
# MEDIA_ROOT = '/usr/local/atiba/AtibaReporting/media'

# setting_files for E-mail Backend;
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_USE_TLS = True
# EMAIL_USE_SSL = False
# EMAIL_HOST = email_production_host
# EMAIL_HOST_USER = email_production_user
# EMAIL_HOST_PASSWORD = email_production_pass
# EMAIL_PORT = 587  # 25 / 465 / 587 port teyid edilmeli!!!

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_COOKIE_AGE = 1*60*60
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True

# Settings for Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'formatter': 'verbose',
            'filename': '/var/log/iamatiba-djangoserver.log',
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
        'handlers': ['file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'views': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False,
        },
        'commons': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False,
        },
        'models': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False,
        },
        'timer': {
            'handlers': ['timer'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'memorytracer': {
            'handlers': ['memorytracer'],
            'level': 'DEBUG',
            'propagate': False,
        }
    },
}


"""
working on linux
from ATIBAreport.setting_files.basesettings import *
from ATIBAreport.setting_files.passes import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']


# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

DATABASE_ROUTERS = [
    'inventories.inventory_router.InventoryRouter',
]

DATABASES = {

    'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': '/usr/local/atiba/AtibaReporting/db.sqlite3',
    },

    'atibadb': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'atibadb',
        'USER': 'atibapg',
        'PASSWORD': 'Gsxr1100!',
        'HOST': '127.0.0.1',
        # 'HOST': '192.168.1.62',
        # 'HOST': '127.0.0.1',
        'PORT': '5432',  # default port
    }
}

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/
# STATIC_URL = '/static/'

#STATICFILES_DIRS = [
#    '/usr/local/atiba/AtibaReporting/static'
#]

STATIC_ROOT = '/usr/local/atiba/AtibaReporting/static'
#STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# MEDIA_ROOT = '/usr/local/atiba/AtibaReporting/media'

# setting_files for E-mail Backend;
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_USE_TLS = True
# EMAIL_USE_SSL = False
# EMAIL_HOST = ''
# EMAIL_HOST_USER = ''
# EMAIL_HOST_PASSWORD = ''
# EMAIL_PORT = 587  # 25 / 465 / 587 port teyid edilmeli!!!


#SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
#CORS_REPLACE_HTTPS_REFERER = True
#HOST_SCHEME = "https://"
#SECURE_PROXY_SSL_HEADER = None
#SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
#SECURE_HSTS_SECONDS = None
#SECURE_HSTS_INCLUDE_SUBDOMAINS = True
#SECURE_FRAME_DENY = True

"""