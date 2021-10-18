from django.db import transaction
from io import StringIO
from logging import getLogger
from pprint import pprint
from pylev import levenshtein

from slacker.listeners import SlackListener


class Dispatcher(object):
    LEADER = '.'

    log = getLogger('Dispatcher')

    def __init__(self, handlers):
        self.handlers = handlers

        self.listeners = [SlackListener(self)]

        messages = []
        commands = {}
        multi_word_commands = {}
        for handler in handlers:
            config = handler.config()
            for command in config.get('commands', []):
                if ' ' in command:
                    multi_word_commands[command] = handler
                else:
                    commands[command] = handler
            if config.get('messages', False):
                messages.append(handler)

        self.commands = commands
        self.multi_word_commands = multi_word_commands
        self.messages = messages

    def urlpatterns(self):
        return sum([l.urlpatterns() for l in self.listeners], [])

    @transaction.atomic
    def added(*args, **kwargs):
        pprint({'type': 'added', 'args': args, 'kwargs': kwargs})

    def _did_you_mean(self, context, command):
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
            f'{self.LEADER}{name}' for score, name in commands if score < cutoff
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

    @transaction.atomic
    def command(self, context, command, text, **kwargs):
        try:
            # look for an exact match single word command
            handler = self.commands[command]
        except KeyError:
            # TODO: this should probably do the splitting/parsing
            command = f'{command} {text}'
            for name, handler in self.multi_word_commands.items():
                if command.startswith(name):
                    text = command.split(name, 1)[1]
                    command = name
                    break

        if not handler:
            self._did_you_mean(context, command)
        else:
            try:
                handler.command(
                    context, command=command, dispatcher=self, **kwargs
                )
            except Exception:
                self.log.exception('Command "%s" failed.', command)
                context.say(
                    f'An error occured while running the `{self.LEADER}{command}` command.'
                )

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
            # TODO: these should all wrap with error handling
            handler.message(*args, **kwargs)

    @transaction.atomic
    def removed(*args, **kwargs):
        pprint({'type': 'removed', 'args': args, 'kwargs': kwargs})
