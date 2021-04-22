#
#
#

from datetime import datetime

from ..event import MessageEvent
from .base import Interaction


class Time(Interaction):
    EVENT_TYPE = MessageEvent
    TRIGGER = 'what time is it'

    def handle(self, message):
        now = datetime.now()
        message.reply(now.strftime('Hi {sender}, it is %H:%M:%S'))
