#
#
#

from logging import getLogger
from pprint import pprint
from slack_bolt import App
from slack_bolt.adapter.tornado import SlackEventsHandler
from tornado.ioloop import IOLoop
from tornado.web import Application, RequestHandler

from ..event import Event
from .event import SlackAddedEvent, SlackJoinedEvent, SlackMessageEvent


# TODO: move this somewhere shared
class StatusHandler(RequestHandler):
    log = getLogger('StatusHandler')

    def get(self):
        self.log.debug('get:')
        self.write('OK')


class SlackException(Exception):
    pass


class SlackAdapter(object):
    logger = getLogger('SlackAdapter')

    # Ignoring most things here, see https://api.slack.com/events/message
    # "Message subtypes"
    INTERESTING = set((
        'message',  # this one is fake/a default
        'message_replied',
    ))

    CHANNEL_TYPES = {
        # on member_joined_channel events
        'C': Event.CHANNEL_PUBLIC,
        'G': Event.CHANNEL_PRIVATE,
        # on message events
        'channel': Event.CHANNEL_PUBLIC,
        'group': Event.CHANNEL_PRIVATE,
        'im': Event.CHANNEL_DIRECT,
    }

    def __init__(self, token, signing_secret):
        self.logger.info('__init__: token=%s, signing_secret=***', token)
        self.slack_app = App(token=token, signing_secret=signing_secret)

        self._info = None

    @property
    def bot_user_id(self):
        if self._info is None:
            resp = self.slack_app.client.auth_test()
            if resp.status_code != 200:
                raise SlackException('failed to retrieve bot info')

            self._info = resp.data
            self.logger.info('bot_user_id: bot info=%s', self._info)

        return self._info['user_id']

    def register(self, simone):
        self.logger.info('register: simone=%s', simone)
        self.simone = simone

        @self.slack_app.event("message")
        def _message(event, *args, **kwargs):
            self.message(event)

        @self.slack_app.event("member_joined_channel")
        def _message(event, *args, **kwargs):
            self.member_joined_channel(event)

        @self.slack_app.event("member_left_channel")
        def _message(event, *args, **kwargs):
            self.member_left_channel(event)

    def message(self, event):
        self.logger.debug('message: event=%s', event)
        if event.get('subtype', 'message') not in self.INTERESTING:
            self.logger.debug('message:   ignoring based on subtype')
            return

        text = event['text']
        channel = event['channel']
        channel_type = event['channel_type']
        thread = event.get('thread_ts', None)

        if channel_type in ('channel', 'im', 'group'):
            sender = event['user']
            if sender == 'USLACKBOT':
                self.logger.debug('message:   ignoring msg from USLACKBOT: '
                                  'text="%s"', text)
                #{
                #    'channel': 'D01UDTE3E8M',
                #    'channel_type': 'im',
                #    'event_ts': '1619046419.000200',
                #    'team': 'T01GZF7DHKN',
                #    'text': 'You have been removed from #bot-dev-private by <@U01GQ7UFKFX>',
                #    'ts': '1619046419.000200',
                #    'type': 'message',
                #    'user': 'USLACKBOT'
                #}
                return
            channel_type = self.CHANNEL_TYPES[event['channel_type']]
            event = SlackMessageEvent(adapter=self, sender=sender, text=text,
                                      channel=channel,
                                      channel_type=channel_type)
        elif channel_type == 'channel_join':
            joiner = event['user']
            sender = event['inviter']
            if joiner == self.bot_user_id:
                # we were added to a room
                event = SlackAddedEvent(adapter=self, sender=sender,
                                        text=text, channel=channel,
                                        channel_type=channel_type)
            else:
                # someone else joined a room we're in
                event = SlackJoinedEvent(adapter=self, sender=sender,
                                         text=text, channel=channel,
                                         channel_type=channel_type,
                                         joiner=joiner)
        else:
            self.logger.warn('message: unexpected channel_type=%s',
                             channel_type)
            return

        self.logger.debug('message:  event=%s', event)
        self.simone.event(event)

    def member_joined_channel(self, event):
        self.logger.debug('member_joined_channel: event=%s', event)

        sender = event['inviter']
        text = ''
        channel = event['channel']
        channel_type = self.CHANNEL_TYPES[event['channel_type']]
        joiner = event['user']
        if joiner == self.bot_user_id:
            # we were added to a room
            event = SlackAddedEvent(adapter=self, sender=sender,
                                    text=text, channel=channel,
                                    channel_type=channel_type)
        else:
            # someone else joined a room we're in
            event = SlackJoinedEvent(adapter=self, sender=sender,
                                     text=text, channel=channel,
                                     channel_type=channel_type,
                                     joiner=joiner)

        self.logger.debug('message:  event=%s', event)
        self.simone.event(event)

    def member_left_channel(self, event):
        # TODO: will this tell us when we leave or do we have to discern that
        # from the USLACKBOT `message`? quick check says USLACKBOT route will
        # be required
        pprint(event)
        return

    def say(self, text, channel, thread_ts=None):
        self.logger.debug('say: text=***, channel=%s, thread_ts=%s', channel,
                          thread_ts)
        # TODO: rich content
        self.slack_app.client.chat_postMessage(channel=channel, text=text,
                                               thread_ts=thread_ts)

    def run(self, address='127.0.0.1', port='4391', debug=False):
        app = Application([
            (r'/slack/events', SlackEventsHandler, dict(app=self.slack_app)),
            (r'/_status', StatusHandler),
        ], debug=debug)

        app.listen(port, address=address)
        # blocks...
        IOLoop.current().start()
