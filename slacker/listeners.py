from django.conf import settings
from enum import Enum, auto
from logging import getLogger
from os import environ
from slack_bolt import App
import re


class ChannelType(Enum):
    PUBLIC = auto()
    PRIVATE = auto()
    DIRECT = auto()

    @classmethod
    def lookup(cls, val):
        return {
            'C': cls.PUBLIC,
            'G': cls.PRIVATE,
            'channel': cls.PUBLIC,
            'group': cls.PRIVATE,
            'im': cls.DIRECT,
        }[val]


class SenderType(Enum):
    USER = auto()
    BOT = auto()


class SlackException(Exception):
    pass


class SlackListener(object):
    _RE_REMOVED_FROM = re.compile(
        r'You have been removed from (?P<channel_name>#[\w\-]+) by <@(?P<user>\w+)>'
    )

    log = getLogger('SlackListener')

    def __init__(self, dispatcher, app=None):
        self.log.info('__init__: dispatcher=%s, app=%s', dispatcher, app)
        self.dispatcher = dispatcher

        if app is None:
            token_verification = getattr(
                settings, 'SLACK_TOKEN_VERIFICATION', False
            )
            app = App(
                token=environ["SLACK_BOT_TOKEN"],
                signing_secret=environ["SLACK_SIGNING_SECRET"],
                token_verification_enabled=token_verification,
            )
        self.app = app
        self._auth_info = None

        @app.event("message")
        def _wrapper_message(event, *args, **kwargs):
            self.message(event)

        @app.event("member_joined_channel")
        def _wrapper_member_joined(event, *args, **kwargs):
            self.member_joined_channel(event)

        @app.event("member_left_channel")
        def _wrapper_member_left(event, *args, **kwargs):
            self.member_left_channel(event)

        # TODO: emit data from auth_info to dispatcher on startup?

    @property
    def auth_info(self):
        '''
        {
            'ok': True,
            'url': 'https://itsbreaktime.slack.com/',
            'team': "It's Break Time",
            'user': 'simone',
            'team_id': 'T01GZF7DHKN',
            'user_id': 'U01V6PW6XDE',
            'bot_id': 'B01UH09KL2E',
            'is_enterprise_install': False
        }
        '''
        if self._auth_info is None:
            resp = self.app.client.auth_test()
            if resp.status_code != 200:
                raise SlackException('failed to retrieve auth_info')

            self._auth_info = resp.data
            self.log.info('auth_info: auth_info=%s', self._auth_info)

        return self._auth_info

    @property
    def bot_user_id(self):
        return self.auth_info['user_id']

    def message(self, event):
        self.log.debug('message: event=%s', event)
        text = event['text']
        channel = event['channel']
        channel_type = event['channel_type']
        team = event.get('team', None)
        thread = event.get('thread_ts', None)
        ts = event['ts']

        subtype = event.get('subtype', None)
        if subtype == 'channel_join':
            # Not interested in these, we'll get them via member_joined_channel
            return

        if channel_type in ('channel', 'im', 'group'):
            if 'user' in event:
                sender = event['user']
                sender_type = SenderType.USER
            else:
                sender = event['bot_id']
                sender_type = SenderType.BOT
            if sender == 'USLACKBOT':
                # TODO: translations?
                match = self._RE_REMOVED_FROM.match(text)
                if match:
                    # The bot has been removed from a channel, the message is
                    # an `im` though so the channel is USLACKBOT's DM with the
                    # bot. We'll have to piece together the info we want here
                    # :-(
                    channel_name = match.group('channel_name')
                    user = match.group('user')
                    self.log.info(
                        'message:   the bot has been removed from %s by %s',
                        channel,
                        user,
                    )
                    # TODO: map channel_name to channel info to get id & type
                    # https://api.slack.com/methods/conversations.list (though
                    # worry when removed from private we wont see it anymore so
                    # maybe stored?
                    self.dispatcher.removed(
                        channel=channel_name,
                        channel_type=None,
                        team=team,
                        remover=user,
                        timestamp=ts,
                    )
                else:
                    self.log.warn(
                        'message:   ignoring other message from USLACKBOT, text=%s',
                        text,
                    )
                return
            channel_type = ChannelType.lookup(channel_type)

            self.dispatcher.message(
                text=text,
                sender=sender,
                sender_type=sender_type,
                channel=channel,
                channel_type=channel_type,
                team=team,
                thread=thread,
                timestamp=ts,
            )
        elif channel_type == 'channel_join':
            # we're not interested in this one, we'll get it through a direct
            # subscription
            self.log.debug('message:   not interested')
        else:
            self.log.warn('message:   unexpected channel_type=%s', channel_type)

    def member_joined_channel(self, event):
        self.log.debug('member_joined_channel: event=%s', event)
        inviter = event.get('inviter', None)
        channel = event['channel']
        channel_type = ChannelType.lookup(event['channel_type'])
        joiner = event['user']
        team = event['team']
        event_ts = event['event_ts']
        if joiner == self.bot_user_id:
            self.dispatcher.added(
                channel=channel,
                channel_type=channel_type,
                team=team,
                inviter=inviter,
                timestamp=event_ts,
            )
        else:
            self.dispatcher.joined(
                joiner=joiner,
                channel=channel,
                channel_type=channel_type,
                team=team,
                inviter=inviter,
                timestamp=event_ts,
            )

    def member_left_channel(self, event):
        self.log.debug('member_left_channel: event=%s', event)
        kicker = event.get('inviter', None)
        channel = event['channel']
        channel_type = ChannelType.lookup(event['channel_type'])
        leaver = event['user']
        team = event['team']
        event_ts = event['event_ts']
        self.dispatcher.left(
            leaver=leaver,
            channel=channel,
            channel_type=channel_type,
            team=team,
            kicker=kicker,
            timestamp=event_ts,
        )

    def say(self, text, channel, thread_ts=None):
        self.log.debug(
            'say: text=***, channel=%s, thread_ts=%s', channel, thread_ts
        )
        # TODO: rich content
        self.app.client.chat_postMessage(
            channel=channel, text=text, thread_ts=thread_ts
        )
