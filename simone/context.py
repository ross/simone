from enum import Enum


class ChannelType(Enum):
    PUBLIC = 'public'
    PRIVATE = 'private'
    DIRECT = 'direct'


class BaseContext(object):
    def __init__(self, channel, channel_type, team, timestamp, thread=None):
        self.channel = channel
        self.channel_type = channel_type
        self.team = team
        self.timestamp = timestamp
        self.thread = thread

    def say(self, text, reply=False):
        raise NotImplementedError('say is not implemented')

    def emote(self, emoji):
        raise NotImplementedError('say is not implemented')

    def __eq__(self, other):
        # only used in tests
        return self.__dict__ == other.__dict__
