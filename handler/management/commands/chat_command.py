from django.core.management.base import BaseCommand
from logging import getLogger

from simone.context import BaseContext, ChannelType, SenderType
from simone.urls import dispatcher


class ConsoleContext(BaseContext):
    def __init__(self, channel_id, channel_name, channel_type, timestamp, bot_user_id):
        super().__init__(channel_id, channel_name, channel_type, timestamp, bot_user_id)

    def say(self, text, reply=False, to_user=False):
        print(text)

    def react(self, emoji):
        self.app.client.reactions_add(
            channel=self.channel_id, name=emoji, timestamp=self.timestamp
        )

    def user_mention(self, user_id):
        return f'<@{user_id}>'

class Command(BaseCommand):
    log = getLogger('ChatCommand')

    def add_arguments(self, parser):
        parser.add_argument('name', nargs='*', type=str)
        parser.add_argument('--force', action='store_true')

    def handle(self, *args, **options):
        channel_id = 'channel-id'
        channel_name = 'channel-name'
        channel_type = ChannelType.PUBLIC
        timestamp = 'when'
        bot_user_id='bot-id'
        context = ConsoleContext(channel_id, channel_name, channel_type, timestamp, bot_user_id)
        text = 'echo ping'
        sender = 'user-id'
        sender_type = SenderType.USER
        mentions = ['other', 'another']
        dispatcher.command(context, text, sender=sender, sender_type=sender_type, mentions=mentions)
