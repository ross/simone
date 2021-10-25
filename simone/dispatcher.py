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
                # We only want to reply to errors on commands
                if 'command' in kwargs:
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
        command_words = {}
        command_max_words = 0
        joineds = []
        messages = []
        for handler in handlers:
            config = handler.config()
            for command in config.get('commands', []):
                command = tuple(command.split())
                commands[' '.join(command)] = handler
                command_words[command] = handler
                command_max_words = max(command_max_words, len(command))
            if config.get('added', False):
                addeds.append(handler)
            if config.get('joined', False):
                joineds.append(handler)
            if config.get('messages', False):
                messages.append(handler)
        self.log.debug('__init__: command_words=%s', command_words)

        self.addeds = addeds
        self.commands = commands
        self.command_words = command_words
        self.command_max_words = command_max_words
        self.joineds = joineds
        self.messages = messages

    def urlpatterns(self):
        return sum([l.urlpatterns() for l in self.listeners], [])

    @dispatch
    def added(self, *args, **kwargs):
        for handler in self.addeds:
            handler.added(*args, **kwargs)

    def _did_you_mean(self, context, command_words):
        # score commands for "distance" from the command we received
        commands = []
        for command in [' '.join(cw) for cw in command_words]:
            commands += [
                (levenshtein(command, name), name)
                for name, _ in self.commands.items()
            ]
        # order them by ascending score
        commands.sort()
        # only include things that are close enough, within 50% matches
        cutoff = len(command) * 0.5
        # as a set to get rid of duplicates
        potentials = set(
            [
                f'{self.LEADER}{name}'
                for score, name in commands
                if score < cutoff
            ]
        )
        # build the response
        buf = StringIO()
        buf.write('Sorry `')
        buf.write(command)
        buf.write('` is not a recognized command.')

        if potentials:
            # in alphabetical order
            potentials = sorted(potentials)
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

    def find_handler(self, text):
        # get rid of any leading and trailing space and generate our command
        # words
        pieces = text.strip().split()
        command_words = [
            tuple(pieces[0:i])
            for i in range(min(len(pieces), self.command_max_words), 0, -1)
        ]
        self.log.debug('find_handler: command_words=%s', command_words)
        # look for matching commands
        for command_word in command_words:
            try:
                handler = self.command_words[command_word]
                # we've found a match
                command = ' '.join(command_word)
                n = len(command_word)
                text = ' '.join(pieces[n:])
                return (command_words, handler, command, text)
            except KeyError:
                pass

        return (command_words, None, None, None)

    @dispatch
    def command(self, context, text, **kwargs):
        '''
        Note: this will clean up whitespace in the command & text
        '''
        command_words, handler, command, text = self.find_handler(text)
        if handler:
            handler.command(
                context, command=command, text=text, dispatcher=self, **kwargs
            )
        else:
            self._did_you_mean(context, command_words)

    @dispatch
    def edit(self, *args, **kwargs):
        pprint({'type': 'edit', 'args': args, 'kwargs': kwargs})

    @dispatch
    def joined(self, *args, **kwargs):
        for handler in self.joineds:
            handler.joined(*args, dispatcher=self, **kwargs)

    @dispatch
    def left(self, *args, **kwargs):
        pprint({'type': 'left', 'args': args, 'kwargs': kwargs})

    @dispatch
    def message(self, *args, **kwargs):
        for handler in self.messages:
            handler.message(*args, dispatcher=self, **kwargs)

    @dispatch
    def removed(self, *args, **kwargs):
        pprint({'type': 'removed', 'args': args, 'kwargs': kwargs})
