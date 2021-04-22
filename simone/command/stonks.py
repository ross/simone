#
#
#

from .base import Command


class Stonks(Command):
    NAME = 'simone-stonks'

    def handle(self, body):
        # TODO:
        from pprint import pprint
        pprint(body)
