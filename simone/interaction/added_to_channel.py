#
#
#

from datetime import datetime

from ..event import AddedEvent
from .base import Interaction


class AddedToChannel(Interaction):
    EVENT_TYPE = AddedEvent

    def handle(self, message):
        message.reply('Thanks for the invite {sender}! Hello everyone :wave:')
