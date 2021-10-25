from logging import getLogger
from random import randrange
import re

from simone.handlers import Registry
from .models import Shout


# Based loosely on https://github.com/desert-planet/hayt/blob/master/scripts/loud.coffee
class Loud(object):
    '''
    Learns and repeats LOUD MESSAGES!
    '''

    log = getLogger('Loud')
    regex = re.compile(r'^\s*(?P<loud>[A-Z"][A-Z0-9 .,\'"()\?!&%$#@+-]+)$')

    def config(self):
        return {'messages': True}

    def message(self, context, text, **kwargs):
        match = self.regex.match(text)
        if match:
            # there's a loud in there
            loud = match.group('loud')
            self.log.debug('message: text=%s, match=%s', text, loud)
            # store it if it's new
            shout, _ = Shout.objects.get_or_create(text=loud)
            # find a random shout to join in with, newest shout will have the
            # max id so pick a random int less than that.
            i = randrange(0, shout.id)
            # then select the first shout with an id greater than or equal to
            # the random int we picked
            shout = Shout.objects.filter(id__gte=i).order_by('id').first()
            self.log.debug('message: i=%d, shout=%s', i, shout)
            if shout:
                # we found something say it
                context.say(shout.text)


Registry.register_handler(Loud())
