from django.db import transaction
from io import StringIO
from pprint import pprint
from pylev import levenshtein

from slacker.listeners import SlackListener


class Dispatcher(object):
    LEADER = '.'

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
            # score commands for "distant" from the command we received
            commands = sorted(
                [
                    (levenshtein(command, name), name)
                    for name, _ in self.commands.items()
                ]
            )
            # only include things that are close enough, within 50% matches
            cutoff = len(command) * 0.5
            potentials = [
                f'{self.LEADER}{name}'
                for score, name in commands
                if score < cutoff
            ]
            # build the response
            buf = StringIO()
            buf.write('Sorry `')
            buf.write(command)
            buf.write('` is not a recognized command.')

            if potentials:
                buf.write(" Maybe you're looking for `")

                last = potentials.pop()
                n = len(potentials)
                if n > 1:
                    buf.write('`, `'.join(potentials))
                    buf.write('`, or `')
                elif n == 1:
                    buf.write(potentials[0])
                    buf.write('` or `')
                buf.write(last)

                buf.write('`.')

            context.say(buf.getvalue())
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
