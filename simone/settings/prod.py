from os import environ

DEBUG = False

STATIC_ROOT = './static'

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

_LEVEL = environ.get('DJANGO_LOGGING_LEVEL', 'INFO')
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
            'level': _LEVEL,
            'formatter': 'simple',
        }
    },
    'root': {'level': _LEVEL, 'handlers': ('console',)},
    'loggers': {'django.db.backends': {'level': 'INFO'}},
}

RESPONDER_COOLDOWN = 3600
