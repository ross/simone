from concurrent.futures import ThreadPoolExecutor
from cron_validator import CronValidator
from datetime import datetime
from django.conf import settings
from django.db import close_old_connections, transaction
from functools import wraps
from opentelemetry import context as otel_context, trace
from opentelemetry.context import Context
from opentelemetry.trace import SpanKind, Status, StatusCode
from io import StringIO
from logging import getLogger
from os import environ, path
from pprint import pformat, pprint
from pylev import levenshtein
from slack_bolt import App
from slack_bolt.oauth.oauth_settings import OAuthSettings
from slack_sdk import WebClient
from slack_sdk.oauth.state_store import FileOAuthStateStore
from time import time
from threading import Event, Thread

from slacker.installation_store import DjangoInstallationStore
from slacker.listeners import SlackListener
from slacker.models import Workspace

max_dispatchers = getattr(settings, 'MAX_DISPATCHERS', 10)
executor = ThreadPoolExecutor(
    max_workers=max_dispatchers, thread_name_prefix='simone-worker'
)

# No-op unless simone/tracing.py configured a real provider, so everything
# below is safe with tracing turned off -- the API's default provider hands
# back non-recording spans.
tracer = trace.get_tracer('simone.dispatcher')


def dispatch_with_error_reporting(func):
    @wraps(func)
    def wrap(self, context, *args, **kwargs):
        ret = None
        # Span outside the transaction so it covers the commit too, which is
        # where a slow write actually shows up. Recording the exception is the
        # point rather than a bonus: this decorator deliberately swallows
        # failures, so without it a broken handler is indistinguishable from a
        # successful request.
        with tracer.start_as_current_span(f'dispatch.{func.__name__}') as span:
            with transaction.atomic():
                try:
                    ret = func(self, context, *args, **kwargs)
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR))
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
        return ret

    return wrap


# TODO: we should put each handler in its own try/except so that if one fails
# it doesn't take out the others
def dispatch(func):
    @wraps(func)
    def wrap(self, context, *args, **kwargs):
        ret = None
        # See dispatch_with_error_reporting above for why the span wraps the
        # transaction and why the exception is recorded explicitly.
        with tracer.start_as_current_span(f'dispatch.{func.__name__}') as span:
            with transaction.atomic():
                try:
                    ret = func(self, context, *args, **kwargs)
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR))
                    self.log.exception(
                        'dispatch failed: context=%s, args=%s, kwargs=%s',
                        context,
                        args,
                        kwargs,
                    )
        return ret

    return wrap


class Dispatcher(object):
    LEADER = '.'
    USER_PLACEHOLDER = '<@user-id>'
    CHANNEL_PLACEHOLDER = '<#channel-id>'

    log = getLogger('Dispatcher')

    def __init__(self, handlers):
        self.handlers = handlers

        # OAuth state files live in <BASE_DIR>/slack_state/ by default; can be
        # overridden via SLACK_STATE_DIR in Django settings.
        state_dir = getattr(settings, 'SLACK_STATE_DIR', None) or path.join(
            settings.BASE_DIR, 'slack_state'
        )

        oauth_settings = OAuthSettings(
            client_id=environ.get('SLACK_CLIENT_ID', ''),
            client_secret=environ.get('SLACK_CLIENT_SECRET', ''),
            scopes=[
                'channels:history',
                'channels:read',
                'chat:write',
                'groups:history',
                'groups:read',
                'groups:write',
                'im:history',
                'im:read',
                'im:write',
                'reactions:write',
            ],
            installation_store=DjangoInstallationStore(),
            state_store=FileOAuthStateStore(
                expiration_seconds=600, base_dir=state_dir
            ),
            install_path='/slack/install',
            redirect_uri_path='/slack/oauth_redirect',
        )

        app = App(
            name='simone',
            signing_secret=environ.get('SLACK_SIGNING_SECRET', ''),
            oauth_settings=oauth_settings,
            listener_executor=executor,
        )
        self.listeners = {'slack': SlackListener(self, app)}

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
                for cron in handler.config().get('crons', []):
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

    @dispatch_with_error_reporting
    def command(self, context, text, **kwargs):
        '''
        Note: this will clean up whitespace in the command & text
        '''
        self.log.debug('command: text=%s, kwargs=%s', text, kwargs)
        command_words, handler, command, text = self.find_command_handler(text)
        if handler:
            # Named for the command, so a trace says *which* command was slow
            # rather than just "a command was". The handler class goes on as an
            # attribute rather than into the name, to keep the name low
            # cardinality.
            with tracer.start_as_current_span(f'command.{command}') as span:
                span.set_attribute('simone.handler', handler.__class__.__name__)
                handler.command(
                    context,
                    command=command,
                    text=text,
                    dispatcher=self,
                    **kwargs,
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
        # Every registered message handler runs on every message, and several
        # do real work per message -- handler_loud's count()+offset fetch,
        # handler_responder's NLTK tokenize, handler_sparkles' read-modify-
        # write. One span each is what makes it obvious which one costs.
        for handler in self.messages:
            name = handler.__class__.__name__
            with tracer.start_as_current_span(f'message.{name}'):
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
            # Fire once per workspace that has the named channel.
            for workspace in Workspace.objects.all():
                try:
                    channel = listener.channel(
                        cron['channel'], workspace=workspace
                    )
                    # we do need to check for channel here as we don't require
                    # them to exist at __init__ time in case we later learn
                    # about them
                    if not channel:
                        self.log.debug(
                            'tick: channel=%s not found for workspace=%s',
                            cron['channel'],
                            workspace,
                        )
                        continue
                    # Build a per-workspace client from the stored bot token
                    # (cron runs outside a Bolt request, so there is no
                    # injected client).
                    client = WebClient(token=workspace.bot_token)
                    context = listener.context(
                        client=client,
                        workspace=workspace,
                        bot_user_id=workspace.bot_user_id,
                        channel=channel,
                    )
                    name = handler.__class__.__name__
                    with tracer.start_as_current_span(f'cron.{name}') as span:
                        span.set_attribute('simone.cron.when', cron['when'])
                        span.set_attribute(
                            'simone.cron.channel', cron['channel']
                        )
                        handler.cron(context, cron=cron, dispatcher=self)
                except Exception as e:
                    trace.get_current_span().record_exception(e)
                    self.log.exception(
                        'tick: cron=%s failed for workspace=%s', cron, workspace
                    )


class Cron(Thread):
    log = getLogger('Cron')

    def __init__(self, dispatcher):
        super().__init__(name='Dispatcher')
        self.dispatcher = dispatcher

    def run(self):
        self.log.info('run: starting')
        # Detach from whatever context started this thread. ThreadingInstrumentor
        # (simone/tracing.py) propagates the spawning context into new threads,
        # which is exactly what we want for slack_bolt's listener executor and
        # wrong here: this thread lives for the life of the process, so anything
        # it inherited would parent every tick, forever, to one long-finished
        # span. Today Cron is started from simone/wsgi.py at import, when no
        # span is active, so this changes nothing -- it's here so that stays
        # true if it's ever started from somewhere else.
        otel_context.attach(Context())
        self.stopper = Event()
        running = True
        while running:
            start = time()
            # Cron is its own thread so we're in the background when tick is
            # called so no need to submit to the executor. we do want to wrap
            # it with try/except to catch handler problems and avoid killing
            # the thread as well as wrap each time around in calls to check
            # our database connections health (name doesn't match
            # functionality)
            #
            # A root span per tick -- its own trace, since nothing requested
            # it. SERVER-ish work with no caller, so INTERNAL is the honest
            # kind. close_old_connections is inside it because reconnect cost
            # is part of what a tick spends.
            with tracer.start_as_current_span(
                'cron.tick', kind=SpanKind.INTERNAL
            ) as span:
                close_old_connections()
                try:
                    self.dispatcher.tick(datetime.utcnow())
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR))
                    self.log.exception('run: tick failed')
                finally:
                    close_old_connections()
            elapsed = time() - start
            pause = 60 - elapsed
            self.log.debug('run:   elapsed=%f, pause=%f', elapsed, pause)
            if pause > 0:
                running = not self.stopper.wait(timeout=pause)
        self.log.info('run: stopped')

    def stop(self):
        self.log.info('stop: stopping')
        self.stopper.set()
