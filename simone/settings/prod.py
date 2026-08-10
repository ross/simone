from os import environ

from django.core.exceptions import ImproperlyConfigured

DEBUG = False


def _require_secret(name):
    '''Read an env var and raise ImproperlyConfigured if it is missing or blank.'''
    value = environ.get(name, '')
    if not value.strip():
        raise ImproperlyConfigured(
            f'{name} must be set to a non-empty value in production'
        )
    return value


SLACK_SIGNING_SECRET = _require_secret('SLACK_SIGNING_SECRET')
SLACK_CLIENT_ID = _require_secret('SLACK_CLIENT_ID')
SLACK_CLIENT_SECRET = _require_secret('SLACK_CLIENT_SECRET')
SIMONE_TOKEN_KEY = _require_secret('SIMONE_TOKEN_KEY')

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
        # mysql-connector-python's own default is connect_timeout=None, i.e.
        # no timeout at all -- a stalled handshake for a new connection (the
        # first thing a freshly forked worker or the Cron thread does) hangs
        # the calling thread forever with nothing logged. Fail loud and fast
        # instead.
        'OPTIONS': {'connect_timeout': 10},
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
