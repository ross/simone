from concurrent.futures import ThreadPoolExecutor
from cron_validator import CronValidator
from datetime import datetime
from django.conf import settings
from django.db import connection, transaction
from functools import wraps
from io import StringIO
from logging import getLogger
from pprint import pformat, pprint
from pylev import levenshtein
from time import time
from threading import Event, Thread

from slacker.listeners import SlackListener


max_dispatchers = getattr(settings, 'MAX_DISPATCHERS', 10)
executor = ThreadPoolExecutor(max_workers=max_dispatchers)


def background(func):
    @wraps(func)
    def submit(*args, **kwargs):
        executor.submit(func, *args, **kwargs)

    return submit


def dispatch_with_error(func):
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
    USER_PLACEHOLDER = '<@user-id>'
    CHANNEL_PLACEHOLDER = '<#channel-id>'

    log = getLogger('Dispatcher')

    def __init__(self, handlers):
        self.handlers = handlers

        self.listeners = {'slack': SlackListener(self)}

        addeds = []
        commands = {}
        command_words = {}
        command_max_words = 0
        joineds = []
        messages = []
        for handler in handlers:
            config = handler.config()
            if config.get('added', False):
                addeds.append(handler)
            for command in config.get('commands', []):
                command = tuple(command.split())
                commands[' '.join(command)] = handler
                command_words[command] = handler
                command_max_words = max(command_max_words, len(command))
            if config.get('joined', False):
                joineds.append(handler)
            if config.get('messages', False):
                messages.append(handler)
        self.log.debug('__init__: command_words=%s', pformat(command_words))

        self.addeds = addeds
        self.commands = commands
        self.command_words = command_words
        self.command_max_words = command_max_words
        self._crons = None
        self.joineds = joineds
        self.messages = messages

    @property
    def crons(self):
        # load crons on demand since validating them requires db access. If we
        # don't delay it we can't do the initial migration etc.
        if self._crons is None:
            self.log.debug('crons: loading')
            crons = []
            for handler in self.handlers:
                for cron in handler.config.get('crons', []):
                    if self.validate_cron(cron):
                        # ^ will have shown warnings and we'll otherwise skip
                        # bad cron configs
                        crons.append((cron, handler))

            self.log.debug('crons: loaded crons=%s', pformat(crons))
            self._crons = crons

        return self._crons

    def urlpatterns(self):
        return sum(
            [l.urlpatterns() for _, l in sorted(self.listeners.items())], []
        )

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

    def find_command_handler(self, text):
        # get rid of any leading and trailing space and generate our command
        # words
        pieces = text.strip().split()
        # create a set of pieces with placeholders as appropriate
        processed_pieces = []
        for piece in pieces:
            if piece.startswith('<@'):
                # user placeholder
                piece = self.USER_PLACEHOLDER
            elif piece.startswith('<#'):
                # channel placeholder
                piece = self.CHANNEL_PLACEHOLDER
            processed_pieces.append(piece)
        n = min(len(processed_pieces), self.command_max_words)
        command_words = [tuple(processed_pieces[0:i]) for i in range(n, 0, -1)]
        self.log.debug('find_command_handler: command_words=%s', command_words)
        # look for matching commands
        for command_word in command_words:
            try:
                handler = self.command_words[command_word]
                # we've found a match
                command = ' '.join(command_word)
                n = len(command_word)
                text = ' '.join(pieces[n:])
                self.log.debug(
                    'find_command_handler: match handler=%s, command=%s, text=%s',
                    handler,
                    command,
                    text,
                )
                return (command_words, handler, command, text)
            except KeyError:
                pass

        self.log.debug('find_command_handler: no match')
        return (command_words, None, None, None)

    @dispatch_with_error
    def command(self, context, text, **kwargs):
        '''
        Note: this will clean up whitespace in the command & text
        '''
        self.log.debug('command: text=%s, kwargs=%s', text, kwargs)
        command_words, handler, command, text = self.find_command_handler(text)
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

    # Cron stuffs

    def validate_cron(self, cron):
        listener = cron['listener']
        if not listener:
            self.log.warning('validate_cron: missing listener, cron=%s', cron)
            return None
        listener = self.listeners[listener]
        if not listener:
            self.log.warning(
                'validate_cron: unrecognized listener=%s', cron.listener
            )
            return None
        channel_name = cron['channel']
        if not channel_name:
            self.log.warning('validate_cron: missing channel, cron=%s', cron)
            return None
        channel = listener.channel(channel_name)
        if not channel:
            self.log.warning(
                'validate: unrecognized channel=%s, listener=%s, keeping cron in case we later learn about it ',
                channel_name,
                listener,
            )
        when = cron.get('when', None)
        if not when:
            self.log.warning('validate_cron: missing when, cron=%s', cron)
            return None
        if not CronValidator.parse(when):
            self.log.warning('validate_cron: invalid when, cron=%s', cron)
            return None

        return cron

    def tick(self, now):
        self.log.debug('tick: ')
        # we've validated things during init so we can just use them here
        for cron, handler in self.crons:
            self.log.debug('tick:   cron=%s, handler=%s', cron, handler)
            if not CronValidator.match_datetime(cron['when'], now):
                # not time
                continue
            listener = self.listeners[cron['listener']]
            channel = listener.channel(cron['channel'])
            # we do need to check for channel here as we don't require them to
            # exist at __init__ time in case we later learn about them
            if not channel:
                self.log.warning(
                    'tick: unrecognized channel=%s, listener=%s',
                    channel,
                    listener,
                )
                continue
            context = listener.context(channel=channel)
            handler.cron(context, cron=cron, dispatcher=self)


class Cron(Thread):
    log = getLogger('Cron')

    def __init__(self, dispatcher):
        super().__init__(name='Dispatcher')
        self.dispatcher = dispatcher

    def run(self):
        self.log.info('run: starting')
        self.stopper = Event()
        running = True
        while running:
            start = time()
            self.dispatcher.tick(datetime.utcnow())
            elapsed = time() - start
            pause = 60 - elapsed
            self.log.debug('run:   elapsed=%f, pause=%f', elapsed, pause)
            if pause > 0:
                running = not self.stopper.wait(timeout=pause)
        self.log.info('run: stopped')

    def stop(self):
        self.log.info('stop: stopping')
        self.stopper.set()
