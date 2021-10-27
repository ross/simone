from django.core.management.base import BaseCommand

from simone.urls import dispatcher
from .base import DispatcherMixin


class Command(DispatcherMixin, BaseCommand):
    name = 'chat_command'

    def dispatch(self, *args, **kwargs):
        dispatcher.command(*args, **kwargs)
