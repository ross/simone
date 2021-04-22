#
#
#

class Event(object):
    CHANNEL_PUBLIC = 'public'
    CHANNEL_PRIVATE = 'private'
    CHANNEL_DIRECT = 'direct'

    def __init__(self, sender, text, channel, channel_type, thread=None):
        '''
        sender: the user/bot that initiated the event
        text: the content/description of the event
        channel: the channel in which the event occured
        channel_type: the type of channel
        thread: the thread identifier, if applicable, for the message
        '''
        self.sender = sender
        self.text = text
        self.channel = channel
        self.thread = thread

    def text_context(self):
        return {
            'sender': self.markup_user(self.sender),
            'channel': self.markup_channel(self.channel),
        }

    def markup_user(self, channel):
        '''
        '''
        raise NotImplementedError('')

    def markup_channel(self, channel):
        '''
        '''
        raise NotImplementedError('')

    def reply(self, text):
        '''
        '''
        raise NotImplementedError('')

    def __repr__(self):
        return f'{self.__class__.__name__}<{self.text}'


class MessageEvent(Event):
    '''
    A user message was seen
    '''


class JoinedEvent(Event):
    '''
    A user was added to a channel
    '''

    def __init__(self, joiner, **kwargs):
        super(JoinedEvent, self).__init__(**kwargs)
        self.joiner = joiner

    def text_context(self):
        ret = super(JoinedEvent, self).text_context()
        ret.update({
            'joiner': self.markup_user(self.joiner),
        })
        return ret


class AddedEvent(Event):
    '''
    The app/bot was added to a channel
    '''
