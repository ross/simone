from enum import Enum


class ChannelType(Enum):
    PUBLIC = 'public'
    PRIVATE = 'private'
    DIRECT = 'direct'


class BaseContext(object):
    def __init__(
        self,
        channel_id,
        channel_name,
        channel_type,
        team,
        timestamp,
        bot_user_id,
        thread=None,
    ):
        self.channel_id = channel_id
        self.channel_name = channel_name
        self.channel_type = channel_type
        self.team = team
        self.timestamp = timestamp
        self.bot_user_id = bot_user_id
        self.thread = thread

    def say(self, text, reply=False, to_user=False):
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
