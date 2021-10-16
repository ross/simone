from django.db import transaction
from pprint import pprint

from slacker.listeners import SlackListener


class Dispatcher(object):
    def __init__(self, handlers):
        self.handlers = handlers

        self.listeners = [SlackListener(self)]

        messages = []
        commands = {}
        for handler in handlers:
            config = handler.config()
            for command in config.get('commands', []):
                commands[command] = handler
            if config.get('messages', False):
                messages.append(handler)

        self.commands = commands
        self.messages = messages

    def urlpatterns(self):
        return sum([l.urlpatterns() for l in self.listeners], [])

    @transaction.atomic
    def added(*args, **kwargs):
        pprint({'type': 'added', 'args': args, 'kwargs': kwargs})

    @transaction.atomic
    def command(self, context, command, **kwargs):
        try:
            handler = self.commands[command]
        except KeyError:
            # TODO: translation support?
            # TODO: respond private or in thread?
            # TODO: generic formatting of text or just adopt slack's?
            # TODO: levenshtein distance to find similar commands?
            context.say(f'Sorry `{command}` is not a recognized command')
        else:
            # TODO: we should catch and log all exceptions down here
            handler.command(context, command=command, dispatcher=self, **kwargs)

    @transaction.atomic
    def edit(*args, **kwargs):
        pprint({'type': 'edit', 'args': args, 'kwargs': kwargs})

    @transaction.atomic
    def joined(*args, **kwargs):
        pprint({'type': 'joined', 'args': args, 'kwargs': kwargs})

    @transaction.atomic
    def left(*args, **kwargs):
        pprint({'type': 'left', 'args': args, 'kwargs': kwargs})

    @transaction.atomic
    def message(self, *args, **kwargs):
        pprint({'type': 'left', 'args': args, 'kwargs': kwargs})
        for handler in self.messages:
            handler.message(*args, **kwargs)

    @transaction.atomic
    def removed(*args, **kwargs):
        pprint({'type': 'removed', 'args': args, 'kwargs': kwargs})
