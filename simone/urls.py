from django.contrib import admin
from django.urls import path

from .dispatcher import Cron, Dispatcher
from .handlers import Registry

Registry.autoload()
dispatcher = Dispatcher(Registry.handlers)
cron = Cron(dispatcher)

urlpatterns = dispatcher.urlpatterns() + [path('adm/', admin.site.urls)]
