from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

DEBUG = True

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
        }
    },
}
