from django.conf import settings
from django.contrib import admin
from django.urls import path
from django.utils.autoreload import file_changed

from .dispatcher import Dispatcher
from .handlers import Registry

Registry.autoload()
dispatcher = Dispatcher(Registry.handlers)


def dispatcher_stop(*args, **kwargs):
    dispatcher.stop()
    dispatcher.join()


if getattr(settings, 'CRON_ENABLED', True):
    dispatcher.start()
    file_changed.connect(dispatcher_stop)

urlpatterns = dispatcher.urlpatterns() + [path('adm/', admin.site.urls)]
