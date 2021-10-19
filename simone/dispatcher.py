from concurrent.futures import ThreadPoolExecutor
from django.conf import settings
from django.db import connection, transaction
from functools import wraps
from io import StringIO
from logging import getLogger
from pprint import pprint
from pylev import levenshtein

from slacker.listeners import SlackListener


max_dispatchers = getattr(settings, 'MAX_DISPATCHERS', 10)
executor = ThreadPoolExecutor(max_workers=max_dispatchers)


def background(func):
    @wraps(func)
    def submit(*args, **kwargs):
        executor.submit(func, *args, **kwargs)

    return submit


def dispatch(func):
    @background
    @wraps(func)
    def wrap(self, context, *args, **kwargs):
        ret = None
        with transaction.atomic():
            try:
                ret = func(self, context, *args, **kwargs)
            except Exception:
                self.log.exception(
                    'dispatch failed: context=%s, args=%s, kwargs=%s',
                    context,
                    args,
                    kwargs,
                )
                context.say(
                    'An error occured while responding to this message',
                    reply=True,
                )
        # We have to close the connection explicitly, if we don't things seem
        # to "hang" somewhere in transaction.atomic() in future jobs :-(
        # This isn't a problem in the dev server with sqlite3, but not clear if
        # that's a difference between mysql and sqlite3 or something about dev
        # mode.
        # TODO: figure out what's going on here to see if we can avoid closing
        connection.close()
        return ret

    return wrap


class Dispatcher(object):
    LEADER = '.'

    log = getLogger('Dispatcher')

    def __init__(self, handlers):
        self.handlers = handlers

        self.listeners = [SlackListener(self)]

        addeds = []
        commands = {}
        joineds = []
        multi_word_commands = {}
        messages = []
        for handler in handlers:
            config = handler.config()
            for command in config.get('commands', []):
                if ' ' in command:
                    multi_word_commands[command] = handler
                else:
                    commands[command] = handler
            if config.get('added', False):
                addeds.append(handler)
            if config.get('joined', False):
                joineds.append(handler)
            if config.get('messages', False):
                messages.append(handler)

        self.addeds = addeds
        self.commands = commands
        self.joineds = joineds
        self.multi_word_commands = multi_word_commands
        self.messages = messages

    def urlpatterns(self):
        return sum([l.urlpatterns() for l in self.listeners], [])

    @dispatch
    def added(self, *args, **kwargs):
        pprint({'type': 'added', 'args': args, 'kwargs': kwargs})
        for handler in self.addeds:
            handler.added(*args, **kwargs)

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

    @dispatch
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
            handler.command(
                context, command=command, text=text, dispatcher=self, **kwargs
            )

    @dispatch
    def edit(self, *args, **kwargs):
        pprint({'type': 'edit', 'args': args, 'kwargs': kwargs})

    @dispatch
    def joined(self, *args, **kwargs):
        pprint({'type': 'joined', 'args': args, 'kwargs': kwargs})
        for handler in self.joineds:
            handler.joined(*args, **kwargs)

    @dispatch
    def left(self, *args, **kwargs):
        pprint({'type': 'left', 'args': args, 'kwargs': kwargs})

    @dispatch
    def message(self, *args, **kwargs):
        pprint({'type': 'left', 'args': args, 'kwargs': kwargs})
        for handler in self.messages:
            handler.message(*args, **kwargs)

    @dispatch
    def removed(self, *args, **kwargs):
        pprint({'type': 'removed', 'args': args, 'kwargs': kwargs})
