from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db' / 'test.sqlite3',
    }
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'simple': {
            'format': '%(asctime)s %(levelname)-5s %(name)s %(message)s',
            'datefmt': '%Y-%m-%dT%H:%M:%SZ',
        }
    },
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
            'level': 'DEBUG',
            'formatter': 'simple',
        }
    },
    'root': {'level': 'DEBUG', 'handlers': ('null',)},
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
