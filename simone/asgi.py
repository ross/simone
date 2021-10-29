"""
ASGI config for simone project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'simone.settings')

application = get_asgi_application()

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
