from django.conf import settings
from django.http import HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.urls import path
from logging import getLogger
from os import environ
from slack_bolt import App
from slack_bolt.adapter.django import SlackRequestHandler
import re

from simone.context import BaseContext, ChannelType, SenderType
from .models import Channel


class SlackException(Exception):
    pass


class SlackContext(BaseContext):
    log = getLogger('SlackContext')

    def __init__(self, app, *args, channel, **kwargs):
        if channel.channel_type == 'public':
            channel_type = ChannelType.PUBLIC
        elif channel.channel_type == 'private':
            channel_type = ChannelType.PRIVATE
        else:
            channel_type = ChannelType.DIRECT
        super().__init__(
            *args,
            channel_id=channel.id,
            channel_name=channel.name,
            channel_type=channel_type,
            **kwargs,
        )
        self.app = app

    def say(self, text, reply=False, to_user=False):
        self.log.debug('say: text=%s, reply=%s', text, reply)
        if to_user:
            self.app.client.chat_postEphemeral(
                channel=self.channel_id,
                text=text,
                thread_ts=self.thread,
                user=to_user,
            )
            return
        if self.thread:
            # if we're already in a thread continue there
            thread = self.thread
            # TODO: support include in main?
        elif reply:
            # if we're asked to reply start a thread
            thread = self.timestamp
        else:
            thread = None
        self.app.client.chat_postMessage(
            channel=self.channel_id, text=text, thread_ts=thread
        )

    def react(self, emoji):
        self.app.client.reactions_add(
            channel=self.channel_id, name=emoji, timestamp=self.timestamp
        )

    def user_mention(self, user_id):
        return f'<@{user_id}>'


class SlackListener(object):
    _RE_REMOVED_FROM = re.compile(
        r'You have been removed from #(?P<channel_name>[\w\-]+) by <@(?P<user>\w+)>'
    )
    _CHANNEL_TYPES = {
        'C': Channel.Type.PUBLIC,
        'G': Channel.Type.PRIVATE,
        'channel': Channel.Type.PUBLIC,
        'group': Channel.Type.PRIVATE,
        'im': Channel.Type.DIRECT,
    }

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
        self._bot_mention = None

        @app.event("message")
        def _wrapper_message(event, *args, **kwargs):
            self.message(event)

        @app.event("member_joined_channel")
        def _wrapper_member_joined(event, *args, **kwargs):
            self.member_joined_channel(event)

        @app.event("member_left_channel")
        def _wrapper_member_left(event, *args, **kwargs):
            self.member_left_channel(event)

        @app.event("channel_rename")
        def _wrapper_channel_rename(event, *args, **kwargs):
            self.channel_rename(event)

        # TODO: emit data from auth_info to dispatcher on startup?

    def urlpatterns(self):

        handler = SlackRequestHandler(app=self.app)

        @csrf_exempt
        def slack_events_handler(request: HttpRequest):
            return handler.handle(request)

        return [path("slack/events", slack_events_handler, name="slack_events")]

    def channel(self, channel_name):
        try:
            return Channel.objects.get(name=channel_name)
        except Channel.DoesNotExist:
            return None

    def context(self, channel=None, thread=None, timestamp=None):
        return SlackContext(
            app=self.app,
            channel=channel,
            thread=thread,
            timestamp=timestamp,
            bot_user_id=self.bot_user_id,
        )

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

    @property
    def bot_mention(self):
        if self._bot_mention is None:
            self._bot_mention = f'<@{self.bot_user_id}>'
        return self._bot_mention

    def _channel_params(self, channel):
        if channel.get('is_private', False):
            channel_type = Channel.Type.PRIVATE
        elif channel.get('is_channel', False):
            channel_type = Channel.Type.PUBLIC
        else:
            channel_type = Channel.Type.DIRECT
        return {
            'id': channel['id'],
            # im's don't have names, fall back to the user
            'name': channel.get('name', None) or channel.get('user', 'n/a'),
            'channel_type': channel_type.value,
        }

    def _channel_info(self, channel_id):
        resp = self.app.client.conversations_info(channel=channel_id)
        return resp.data['channel']

    def _get_or_create_channel(self, channel_id):
        try:
            return Channel.objects.get(id=channel_id)
        except Channel.DoesNotExist:
            pass
        channel = self._channel_info(channel_id)
        params = self._channel_params(channel)
        return Channel.objects.create(**params)

    def channel_rename(self, event):
        self.log.debug('channel_rename: event=%s', event)
        params = self._channel_params(event['channel'])
        channel_id = params.pop('id')
        channel, _ = Channel.objects.update_or_create(
            id=channel_id, defaults=params
        )

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

        channel_id = event['channel']
        slack_channel_type = event['channel_type']

        if slack_channel_type == 'channel_join':
            # we're not interested in this one, we'll get it through
            # member_joined_channel
            self.log.debug('message:   not interested')
            return
        elif slack_channel_type not in ('channel', 'im', 'group'):
            self.log.warn(
                'message:   unexpected slack_channel_type=%s',
                slack_channel_type,
            )
            return

        channel = self._get_or_create_channel(channel_id)
        text = message['text']

        thread = event.get('thread_ts', None)
        ts = event['ts']

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
                channel_name = match.group('channel_name')
                user = match.group('user')
                self.log.info(
                    'message:   the bot has been removed from %s by %s',
                    channel_name,
                    user,
                )
                try:
                    removed_from = Channel.objects.get(name=channel_name)
                except Channel.DoesNotExist:
                    self.log.warn(
                        'message: removed from channel (%s) we do not recognize',
                        channel_name,
                    )
                    return
                self.dispatcher.removed(
                    context=self.context(channel=removed_from, timestamp=ts),
                    remover=user,
                )
            else:
                self.log.warn(
                    'message:   ignoring other message from USLACKBOT, text=%s',
                    text,
                )
            return

        bot_user_id = self.bot_user_id
        try:
            mentions = []
            for i, block in enumerate(message['blocks']):
                for j, element in enumerate(block['elements']):
                    for k, element in enumerate(element['elements']):
                        if element['type'] == 'user':
                            user_id = element['user_id']
                            # ignore first mention of the bot_user_id,
                            # it's starting a command
                            if i + j + k != 0 or user_id != bot_user_id:
                                mentions.append(element['user_id'])
        except KeyError:
            mentions = []

        if previous_text is not None:
            # Note: we ignore any edited commands
            self.dispatcher.edit(
                context=self.context(
                    channel=channel, thread=thread, timestamp=ts
                ),
                text=text,
                previous_text=previous_text,
                sender=sender,
                sender_type=sender_type,
                previous_timestamp=previous_timestamp,
                mentions=mentions,
            )
        else:
            if text.startswith(self.bot_mention):
                text = text.replace(f'{self.bot_mention} ', '', 1)
                self.dispatcher.command(
                    context=self.context(
                        channel=channel, thread=thread, timestamp=ts
                    ),
                    text=text,
                    sender=sender,
                    sender_type=sender_type,
                    mentions=mentions,
                )
            elif (
                text.startswith(self.dispatcher.LEADER)
                and text[len(self.dispatcher.LEADER)] != ' '
            ):
                text = text.replace(self.dispatcher.LEADER, '', 1)
                self.dispatcher.command(
                    context=self.context(
                        channel=channel, thread=thread, timestamp=ts
                    ),
                    text=text,
                    sender=sender,
                    sender_type=sender_type,
                    mentions=mentions,
                )
            else:
                self.dispatcher.message(
                    context=self.context(
                        channel=channel, thread=thread, timestamp=ts
                    ),
                    text=text,
                    sender=sender,
                    sender_type=sender_type,
                    mentions=mentions,
                )

    def member_joined_channel(self, event):
        self.log.debug('member_joined_channel: event=%s', event)
        inviter = event.get('inviter', None)
        channel = event['channel']
        channel = self._get_or_create_channel(channel)
        joiner = event['user']
        event_ts = event['event_ts']
        if joiner == self.bot_user_id:
            self.dispatcher.added(
                context=self.context(channel=channel, timestamp=event_ts),
                inviter=inviter,
            )
        else:
            self.dispatcher.joined(
                context=self.context(channel=channel, timestamp=event_ts),
                joiner=joiner,
                inviter=inviter,
            )

    def member_left_channel(self, event):
        self.log.debug('member_left_channel: event=%s', event)
        kicker = event.get('inviter', None)
        channel = event['channel']
        channel = self._get_or_create_channel(channel)
        leaver = event['user']
        event_ts = event['event_ts']
        self.dispatcher.left(
            context=self.context(channel=channel, timestamp=event_ts),
            leaver=leaver,
            kicker=kicker,
        )
