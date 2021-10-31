from os import environ
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

DEBUG = True

CRON_ENABLED = False


if 'SIMONE_DB_NAME' in environ:
    DATABASES = {
        'default': {
            'ENGINE': 'mysql.connector.django',
            'NAME': environ['SIMONE_DB_NAME'],
            'USER': environ['SIMONE_DB_USER'],
            'PASSWORD': environ['SIMONE_DB_PASSWORD'],
            'HOST': environ['SIMONE_DB_HOST'],
            'PORT': environ.get('SIMONE_DB_PORT', '3306'),
            'CONN_MAX_AGE': 300,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db' / 'db.sqlite3',
        }
    }

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '%(asctime)s %(levelname)-5s %(name)s %(message)s',
            'datefmt': '%Y-%m-%dT%H:%M:%SZ',
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.handlers.WatchedFileHandler',
            'level': 'DEBUG',
            'formatter': 'simple',
            'filename': 'django.log',
        },
    },
    'root': {'level': 'DEBUG', 'handlers': ('console', 'file')},
    'loggers': {
        'django.db.backends': {
            # comment out to see db queries
            'level': 'INFO'
        },
        'slack_bolt': {
            # super noisy
            'level': 'INFO'
        },
    },
}
