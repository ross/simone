from os import environ

DEBUG = False

STATIC_ROOT = './static'

CSRF_TRUSTED_ORIGINS = ['https://simone.xormedia.com']

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

# OAuth state files (10-min CSRF tokens during /slack/install flow).
# Container-local is fine; losing them on restart just means in-flight
# install attempts get a CSRF error and the user retries.
SLACK_STATE_DIR = '/app/slack_state'

# OAuth state files (10-min CSRF tokens during /slack/install flow).
# Container-local is fine; losing them on restart just means any in-flight
# install attempts get a CSRF error and the user retries.
SLACK_STATE_DIR = '/app/slack_state'
