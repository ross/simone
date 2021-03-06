from enum import Enum
from time import sleep


class ChannelType(Enum):
    PUBLIC = 'public'
    PRIVATE = 'private'
    DIRECT = 'direct'


class SenderType(Enum):
    USER = 'user'
    BOT = 'bot'


class BaseContext(object):
    def __init__(
        self,
        channel_id,
        channel_name,
        channel_type,
        timestamp,
        bot_user_id,
        thread=None,
    ):
        self.channel_id = channel_id
        self.channel_name = channel_name
        self.channel_type = channel_type
        self.timestamp = timestamp
        self.bot_user_id = bot_user_id
        self.thread = thread

    def say(self, text, reply=False, to_user=False, pauses=None):
        '''
        reply: Controls whether a new thread is started with the message
            - False: the text will be sent in the main channel unless it was
                  already in a thread in which case the it will continue there.
            - True: the text will be sent as a reply to the context triggering
                  event. If the context was already in a thread it will
                  continue there.
        to_user: Controls the visibility of the message.
            - False: a public response that everyone will be able to see
            - <user-id>: a private message only visible to the specified user.
        '''
        raise NotImplementedError('say is not implemented')

    def converse(self, texts, pauses=None, **kwargs):
        for i, text in enumerate(texts):
            self.say(text, **kwargs)
            try:
                pause = pauses[i]
            except (IndexError, TypeError):
                # The average human can type 190 to 200 wpm, simone is above
                # average and not human so let's say 225.
                # 225 wpm / 60 s = 3.75 wsp
                pause = len(text.split(' ')) / 3.75
            sleep(pause)

    def react(self, emoji):
        '''
        emoji: The emoji to attach to the message that generated this event.
        '''
        raise NotImplementedError('say is not implemented')

    def user_mention(self, user_id):
        raise NotImplementedError('user_mention is not implemented')

    def __eq__(self, other):
        # only used in tests
        return self.__dict__ == other.__dict__

    def __repr__(self):
        return f'{self.__dict__}'


class ConsoleContext(BaseContext):
    '''
    Useful for development & testing purposes
    '''

    def __init__(
        self, channel_id, channel_name, channel_type, timestamp, bot_user_id
    ):
        super().__init__(
            channel_id, channel_name, channel_type, timestamp, bot_user_id
        )

    def say(self, text, reply=False, to_user=False):
        if to_user:
            text = f'{to_user}> {text}'
        elif reply:
            text = f'> {text}'
        print(text)

    def react(self, emoji):
        self.app.client.reactions_add(
            channel=self.channel_id, name=emoji, timestamp=self.timestamp
        )

    def user_mention(self, user_id):
        return f'<{user_id}>'
