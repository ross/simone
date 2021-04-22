#
#
#

from ..event import AddedEvent, JoinedEvent, MessageEvent


class SlackContext(object):

    def __init__(self, adapter, **kwargs):
        super(SlackContext, self).__init__(**kwargs)
        self.adapter = adapter

    def reply(self, text):
        # format the message, replacing {...} with real values
        text = text.format(**self.text_context())

        # Reply in the channel...and in thread if the event occured in one
        # TODO: error handling?
        self.adapter.say(text=text, channel=self.channel,
                         thread_ts=self.thread)
        return True

    def markup_channel(self, channel):
        return f'<#{channel}>'

    def markup_user(self, user):
        return f'<@{user}>'


class SlackMessageEvent(SlackContext, MessageEvent):
    pass


class SlackJoinedEvent(SlackContext, JoinedEvent):
    pass


class SlackAddedEvent(SlackContext, AddedEvent):
    pass
