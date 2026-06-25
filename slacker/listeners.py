from django.http import HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.urls import path
from logging import getLogger
from slack_bolt.adapter.django import SlackRequestHandler
import re

from simone.context import BaseContext, ChannelType, SenderType
from .models import Channel, Workspace


class SlackException(Exception):
    pass


class SlackContext(BaseContext):
    log = getLogger('SlackContext')

    def __init__(self, client, *args, channel, workspace=None, **kwargs):
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
            workspace=workspace,
            **kwargs,
        )
        self.client = client

    def say(self, text, reply=False, to_user=False):
        self.log.debug('say: text=%s, reply=%s', text, reply)
        if to_user:
            self.client.chat_postEphemeral(
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
        self.client.chat_postMessage(
            channel=self.channel_id, text=text, thread_ts=thread
        )

    def react(self, emoji):
        self.client.reactions_add(
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

    def __init__(self, dispatcher, app):
        self.log.info('__init__: dispatcher=%s, app=%s', dispatcher, app)
        self.dispatcher = dispatcher
        self.app = app

        @app.event("message")
        def _wrapper_message(event, client, context, *args, **kwargs):
            self.message(event, client=client, bolt_context=context)

        @app.event("member_joined_channel")
        def _wrapper_member_joined(event, client, context, *args, **kwargs):
            self.member_joined_channel(
                event, client=client, bolt_context=context
            )

        @app.event("member_left_channel")
        def _wrapper_member_left(event, client, context, *args, **kwargs):
            self.member_left_channel(event, client=client, bolt_context=context)

        @app.event("channel_rename")
        def _wrapper_channel_rename(event, client, context, *args, **kwargs):
            self.channel_rename(event, client=client, bolt_context=context)

        # TODO: emit data from auth_info to dispatcher on startup?

    def urlpatterns(self):

        handler = SlackRequestHandler(app=self.app)

        @csrf_exempt
        def slack_handler(request: HttpRequest):
            return handler.handle(request)

        return [
            path("slack/events", slack_handler, name="slack_events"),
            path("slack/install", slack_handler, name="slack_install"),
            path(
                "slack/oauth_redirect",
                slack_handler,
                name="slack_oauth_redirect",
            ),
        ]

    def channel(self, channel_name, workspace=None):
        '''
        Look up a Channel by name, optionally scoped to a workspace.
        workspace scoping is enforced after step 6 adds the FK; for now
        the lookup is global (correct for single-workspace cron use in step 7).
        '''
        try:
            return Channel.objects.get(name=channel_name)
        except Channel.DoesNotExist:
            return None

    def context(
        self,
        client=None,
        workspace=None,
        bot_user_id=None,
        channel=None,
        thread=None,
        timestamp=None,
    ):
        '''Build a SlackContext.

        When called from event handlers, pass explicit client/workspace/bot_user_id
        from the Bolt per-request context.  When called from cron (step 7), those
        will be supplied per-workspace as well.  Until step 7 lands, cron calls
        that omit client/workspace continue to use self.app.client as a fallback.
        '''
        return SlackContext(
            client=client or self.app.client,
            channel=channel,
            thread=thread,
            timestamp=timestamp,
            bot_user_id=bot_user_id or 'unknown',
            workspace=workspace,
        )

    def _get_workspace(self, team_id):
        try:
            return Workspace.objects.get(team_id=team_id)
        except Workspace.DoesNotExist:
            self.log.error(
                '_get_workspace: unknown team_id=%s; has this workspace installed the app?',
                team_id,
            )
            return None

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

    def _channel_info(self, client, channel_id):
        resp = client.conversations_info(channel=channel_id)
        return resp.data['channel']

    def _get_or_create_channel(self, client, channel_id):
        try:
            return Channel.objects.get(id=channel_id)
        except Channel.DoesNotExist:
            pass
        channel = self._channel_info(client, channel_id)
        params = self._channel_params(channel)
        return Channel.objects.create(**params)

    def channel_rename(self, event, client, bolt_context):
        self.log.debug('channel_rename: event=%s', event)
        params = self._channel_params(event['channel'])
        channel_id = params.pop('id')
        channel, _ = Channel.objects.update_or_create(
            id=channel_id, defaults=params
        )

    def message(self, event, client, bolt_context):
        self.log.debug('message: event=%s', event)

        team_id = bolt_context['team_id']
        workspace = self._get_workspace(team_id)
        if workspace is None:
            return
        bot_user_id = bolt_context['bot_user_id']
        bot_mention = f'<@{bot_user_id}>'

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

        channel = self._get_or_create_channel(client, channel_id)
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
                    context=self.context(
                        client=client,
                        workspace=workspace,
                        bot_user_id=bot_user_id,
                        channel=removed_from,
                        timestamp=ts,
                    ),
                    remover=user,
                )
            else:
                self.log.warn(
                    'message:   ignoring other message from USLACKBOT, text=%s',
                    text,
                )
            return

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
                    client=client,
                    workspace=workspace,
                    bot_user_id=bot_user_id,
                    channel=channel,
                    thread=thread,
                    timestamp=ts,
                ),
                text=text,
                previous_text=previous_text,
                sender=sender,
                sender_type=sender_type,
                previous_timestamp=previous_timestamp,
                mentions=mentions,
            )
        else:
            if text.startswith(bot_mention):
                text = text.replace(f'{bot_mention} ', '', 1)
                self.dispatcher.command(
                    context=self.context(
                        client=client,
                        workspace=workspace,
                        bot_user_id=bot_user_id,
                        channel=channel,
                        thread=thread,
                        timestamp=ts,
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
                        client=client,
                        workspace=workspace,
                        bot_user_id=bot_user_id,
                        channel=channel,
                        thread=thread,
                        timestamp=ts,
                    ),
                    text=text,
                    sender=sender,
                    sender_type=sender_type,
                    mentions=mentions,
                )
            else:
                self.dispatcher.message(
                    context=self.context(
                        client=client,
                        workspace=workspace,
                        bot_user_id=bot_user_id,
                        channel=channel,
                        thread=thread,
                        timestamp=ts,
                    ),
                    text=text,
                    sender=sender,
                    sender_type=sender_type,
                    mentions=mentions,
                )

    def member_joined_channel(self, event, client, bolt_context):
        self.log.debug('member_joined_channel: event=%s', event)
        team_id = bolt_context['team_id']
        workspace = self._get_workspace(team_id)
        if workspace is None:
            return
        bot_user_id = bolt_context['bot_user_id']
        inviter = event.get('inviter', None)
        channel = event['channel']
        channel = self._get_or_create_channel(client, channel)
        joiner = event['user']
        event_ts = event['event_ts']
        if joiner == bot_user_id:
            self.dispatcher.added(
                context=self.context(
                    client=client,
                    workspace=workspace,
                    bot_user_id=bot_user_id,
                    channel=channel,
                    timestamp=event_ts,
                ),
                inviter=inviter,
            )
        else:
            self.dispatcher.joined(
                context=self.context(
                    client=client,
                    workspace=workspace,
                    bot_user_id=bot_user_id,
                    channel=channel,
                    timestamp=event_ts,
                ),
                joiner=joiner,
                inviter=inviter,
            )

    def member_left_channel(self, event, client, bolt_context):
        self.log.debug('member_left_channel: event=%s', event)
        team_id = bolt_context['team_id']
        workspace = self._get_workspace(team_id)
        if workspace is None:
            return
        bot_user_id = bolt_context['bot_user_id']
        kicker = event.get('inviter', None)
        channel = event['channel']
        channel = self._get_or_create_channel(client, channel)
        leaver = event['user']
        event_ts = event['event_ts']
        self.dispatcher.left(
            context=self.context(
                client=client,
                workspace=workspace,
                bot_user_id=bot_user_id,
                channel=channel,
                timestamp=event_ts,
            ),
            leaver=leaver,
            kicker=kicker,
        )
