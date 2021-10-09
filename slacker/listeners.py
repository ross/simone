from django.conf import settings
from enum import Enum, auto
from logging import getLogger
from os import environ
from slack_bolt import App


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
        }


# bot added to a public channel
# member_joined_channel = {
#    'type': 'member_joined_channel',
#    'user': 'U01V6PW6XDE',
#    'channel': 'C01GTHYEU4B',
#    'channel_type': 'C',
#    'team': 'T01GZF7DHKN',
#    'inviter': 'U01GQ7UFKFX',
#    'event_ts': '1633815284.005500'
# }
#
# bot removed from public channel
# message = {
#    'type': 'message',
#    'text': 'You have been removed from #bot-dev by <@U01GQ7UFKFX>',
#    'user': 'USLACKBOT',
#    'ts': '1633814854.000100',
#    'team': 'T01GZF7DHKN',
#    'channel': 'D01UDTE3E8M',
#    'event_ts': '1633814854.000100',
#    'channel_type': 'im'
# }
#
# message from a user in a public channel
# message = {
#    'client_msg_id': '2a549133-9301-4099-9518-dc1e1a7df4ef',
#    'type': 'message',
#    'text': 'testing',
#    'user': 'U01GQ7UFKFX',
#    'ts': '1633815504.005800',
#    'team': 'T01GZF7DHKN',
#    'blocks': [{'type': 'rich_text',
#                'block_id': 'PNWH',
#                'elements': [{'type': 'rich_text_section',
#                              'elements': [{'type': 'text',
#                                            'text': 'testing'}]}]}],
#    'channel': 'C01GTHYEU4B',
#    'event_ts': '1633815504.005800',
#    'channel_type': 'channel'
# }
#
# message from a user in a public channel thread
# message = {
#    'client_msg_id': '73da774c-a7e2-42a3-9a09-eb2b0fa3b8b7',
#    'type': 'message',
#    'text': 'in a thread',
#    'user': 'U01GQ7UFKFX',
#    'ts': '1633815602.006000',
#    'team': 'T01GZF7DHKN',
#    'blocks': [{'type': 'rich_text',
#                'block_id': 'Yb3X+',
#                'elements': [{'type': 'rich_text_section',
#                              'elements': [{'type': 'text',
#                                            'text': 'in a thread'}]}]}],
#    'thread_ts': '1633815504.005800',
#    'parent_user_id': 'U01GQ7UFKFX',
#    'channel': 'C01GTHYEU4B',
#    'event_ts': '1633815602.006000',
#    'channel_type': 'channel'
# }
#
# user leaves a public channel
# member_left_channel = {
#    'type': 'member_left_channel',
#    'user': 'U01GQ7UFKFX',
#    'channel': 'C01GTHYEU4B',
#    'channel_type': 'C',
#    'team': 'T01GZF7DHKN',
#    'event_ts': '1633815668.006400'
# }
#
# user joins a public channel
# message = {
#    'type': 'message',
#    'subtype': 'channel_join',
#    'ts': '1633815843.006600',
#    'user': 'U01GQ7UFKFX',
#    'text': '<@U01GQ7UFKFX> has joined the channel',
#    'channel': 'C01GTHYEU4B',
#    'event_ts': '1633815843.006600',
#    'channel_type': 'channel'
# }
# member_joined_channel = {
#    'type': 'member_joined_channel',
#    'user': 'U01GQ7UFKFX',
#    'channel': 'C01GTHYEU4B',
#    'channel_type': 'C',
#    'team': 'T01GZF7DHKN',
#    'event_ts': '1633815843.006500'
# }
#
# bot removed from a private channel
# message = {
#    'type': 'message',
#    'text': 'You have been removed from #bot-dev-private by <@U01GQ7UFKFX>',
#    'user': 'USLACKBOT',
#    'ts': '1633816442.000100',
#    'team': 'T01GZF7DHKN',
#    'channel': 'D01UDTE3E8M',
#    'event_ts': '1633816442.000100',
#    'channel_type': 'im'
# }
#
# bot is added to a private channel
# member_joined_channel = {
#    'type': 'member_joined_channel',
#    'user': 'U01V6PW6XDE',
#    'channel': 'C01UTGR299A',
#    'channel_type': 'C',
#    'team': 'T01GZF7DHKN',
#    'inviter': 'U01GQ7UFKFX',
#    'event_ts': '1633816538.000800'
# }
#
# message from a user in a private channel
# message = {
#    'client_msg_id': 'e8c9c128-d781-4f48-8811-3d3fca32e416',
#    'type': 'message',
#    'text': 'boo',
#    'user': 'U01GQ7UFKFX',
#    'ts': '1633816328.000200',
#    'team': 'T01GZF7DHKN',
#    'blocks': [{'type': 'rich_text',
#                'block_id': 'Tp7',
#                'elements': [{'type': 'rich_text_section',
#                              'elements': [{'type': 'text',
#                                            'text': 'boo'}]}]}],
#    'channel': 'C01UTGR299A',
#    'event_ts': '1633816328.000200',
#    'channel_type': 'group'
# }


class SlackAdapter(object):
    log = getLogger('SlackAdapter')

    def __init__(self, app):
        self.app = app

        @app.event("message")
        def _wrapper_message(event, *args, **kwargs):
            self.message(event)

        @app.event("member_joined_channel")
        def _wrapper_member_joined(event, *args, **kwargs):
            self.member_joined_channel(event)

        @app.event("member_left_channel")
        def _wrapper_member_left(event, *args, **kwargs):
            self.member_left_channel(event)

    def message(self, event):
        self.log.debug('message: event=%s', event)
        text = event['text']
        channel = event['channel']
        channel_type = event['channel_type']
        thread = event.get('thread_ts', None)

        if channel_type in ('channel', 'im', 'group'):
            sender = event['user']
            if sender == 'USLACKBOT':
                if text.startswith('You have been removed from'):
                    # The bot has been removed from a channel
                    self.log.info(
                        'message:   the bot has been removed from %s', channel
                    )
                    # TODO: should we do anything here
                else:
                    self.log.warn(
                        'message:   ignoring other message from USLACKBOT, text=%s',
                        text,
                    )
                return
            channel_type = ChannelType.lookup(channel_type)
            # TODO: see who wants it...
        elif channel_type == 'channel_join':
            # we're not interested in this one, we'll get it through a direct
            # subscription
            self.log.debug('message:   not interested')
        else:
            self.log.warn('message:   unexpected channel_type=%s', channel_type)

        self.say(
            f'hi <@{sender}>, you said {text} in <#{channel}>', channel, thread
        )

    def member_joined_channel(self, event):
        self.log.debug('member_joined_channel: event=%s', event)
        # TODO: handle this, maybe say hi to everone

    def member_left_channel(self, event):
        self.log.debug('member_left_channel: event=%s', event)
        # TODO: shoudl we do anything here

    def say(self, text, channel, thread_ts=None):
        self.log.debug(
            'say: text=***, channel=%s, thread_ts=%s', channel, thread_ts
        )
        # TODO: rich content
        self.app.client.chat_postMessage(
            channel=channel, text=text, thread_ts=thread_ts
        )


app = App(
    token=environ["SLACK_BOT_TOKEN"],
    signing_secret=environ["SLACK_SIGNING_SECRET"],
    token_verification_enabled=not settings.DEBUG,
)
adapter = SlackAdapter(app)
