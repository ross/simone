#
#
#

from .base import Command


class Stonks(Command):
    NAME = 'stonks'

    def help(self, event):
        event.reply('TODO: help')

    def handle(self, event):
        event.reply('TODO: stuff')
