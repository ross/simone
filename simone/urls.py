from django.contrib import admin
from django.urls import path

from .dispatcher import Dispatcher
from .handlers import Registry

Registry.autoload()
dispatcher = Dispatcher(Registry.handlers)

urlpatterns = dispatcher.urlpatterns() + [path('adm/', admin.site.urls)]
