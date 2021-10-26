from logging import getLogger
from time import time

from simone.context import ConsoleContext, ChannelType, SenderType


class DispatcherMixin(object):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log = getLogger(self.name)

    def add_arguments(self, parser):
        parser.add_argument('text', nargs='+', type=str)
        parser.add_argument('--bot-user-id', type=str, default='bot-user-id')
        parser.add_argument('--channel-id', type=str, default='channel-id')
        parser.add_argument('--channel-name', type=str, default='greetings')
        parser.add_argument('--channel-type', type=str, default='public')
        parser.add_argument('--sender', type=str, default='user-id')
        parser.add_argument('--sender-type', type=str, default='user')
        parser.add_argument('--timestamp', type=float)
        parser.add_argument('--mentions', nargs='*', type=str, default=[])

    def handle(self, *args, **options):
        channel_id = options['channel_id']
        channel_name = options['channel_name']
        channel_type = ChannelType(options['channel_type'])
        timestamp = options.get('timestamp', time())
        bot_user_id = options['bot_user_id']
        context = ConsoleContext(
            channel_id, channel_name, channel_type, timestamp, bot_user_id
        )
        text = ' '.join(options['text'])
        if text.startswith('.'):
            text = text[1:]
        sender = options['sender']
        sender_type = SenderType(options['sender_type'])
        mentions = options['mentions']
        self.dispatch(
            context,
            text,
            sender=sender,
            sender_type=sender_type,
            mentions=mentions,
        )
