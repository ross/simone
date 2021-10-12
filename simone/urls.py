from django.contrib import admin
from django.urls import path

from .dispatcher import Dispatcher

dispatcher = Dispatcher()

urlpatterns = dispatcher.urlpatterns() + [path('admin/', admin.site.urls)]
