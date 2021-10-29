"""
WSGI config for simone project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'simone.settings')

application = get_wsgi_application()

# needs to come after the os.environ bit above
from django.conf import settings  # noqa
from django.utils.autoreload import file_changed  # noqa

from simone.urls import cron  # noqa

if getattr(settings, 'CRON_ENABLED', True):

    def cron_stop(*args, **kwargs):
        cron.stop()
        cron.join()

    cron.start()
    file_changed.connect(cron_stop)
