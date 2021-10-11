from django.conf import settings
from enum import Enum, auto
from logging import getLogger
from os import environ
from slack_bolt import App
import re

from .models import Channel


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

        subtype = event.get('subtype', None)
        if subtype == 'channel_join':
            # Not interested in these, we'll get them via member_joined_channel
            return
        elif subtype == 'message_changed':
            message = event['message']
            previous = event['previous_message']
            previous_text = previous['text']
            previous_timestamp = previous['ts']
        else:
            message = event
            previous_text = None
            previous_timestamp = None

        channel = event['channel']
        channel_type = event['channel_type']

        text = message['text']
        team = message.get('team', None)

        thread = event.get('thread_ts', None)
        ts = event['ts']

        if channel_type in ('channel', 'im', 'group'):
            if 'user' in message:
                sender = message['user']
                sender_type = SenderType.USER
            else:
                sender = message['bot_id']
                sender_type = SenderType.BOT

            if sender == 'USLACKBOT':
                # TODO: translations?
                match = self._RE_REMOVED_FROM.match(text)
                if match:
                    # work around the lack of info in the removed message by
                    # looking up our stored channel info
                    name = match.group('channel_name')
                    try:
                        channel = Channel.objects.get(team_id=team, name=name)
                        channel_type = channel.channel_type
                        channel = channel.id
                    except Channel.DoesNotExist:
                        self.log.warn(
                            'message: removed from an unknown channel, team=%s, name=%s',
                            team,
                            name,
                        )
                        channel = name
                        channel_type = None

                    user = match.group('user')
                    self.log.info(
                        'message:   the bot has been removed from %s by %s',
                        channel,
                        user,
                    )
                    self.dispatcher.removed(
                        channel=channel,
                        channel_type=channel_type,
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
            channel_type = Channel.Type.lookup(channel_type)

            if previous_text is not None:
                self.dispatcher.edit(
                    text=text,
                    previous_text=previous_text,
                    sender=sender,
                    sender_type=sender_type,
                    channel=channel,
                    channel_type=channel_type,
                    team=team,
                    thread=thread,
                    timestamp=ts,
                    previous_timestamp=previous_timestamp,
                )
            else:
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
        team = event['team']
        channel_type = self._channel_type(channel, team)
        joiner = event['user']
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

    def _channel_info(self, channel_id):
        resp = self.app.client.conversations_info(channel=channel_id)
        return resp.data['channel']

    def _channel_type(self, channel_id, team_id):
        '''
        Return the channel_type and fetch info and record channel in the db if
        not already there.
        '''
        try:
            channel = Channel.objects.get(id=channel_id)
            return channel.channel_type
        except Channel.DoesNotExist:
            pass
        channel = self._channel_info(channel_id)
        if channel['is_channel']:
            channel_type = Channel.Type.PUBLIC
        elif channel['is_group']:
            channel_type = Channel.Type.PRIVATE
        else:
            channel_type = Channel.Type.DIRECT
        Channel.objects.create(
            id=channel['id'],
            team_id=team_id,
            name=channel['name'],
            channel_type=channel_type,
        )
        return channel_type

    def member_left_channel(self, event):
        self.log.debug('member_left_channel: event=%s', event)
        kicker = event.get('inviter', None)
        channel = event['channel']
        channel_type = Channel.Type.lookup(event['channel_type'])
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
