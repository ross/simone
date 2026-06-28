from logging import getLogger
from random import randrange
import re

from simone.handlers import Registry, exclude_private
from .models import Shout


# Based loosely on https://github.com/desert-planet/hayt/blob/master/scripts/loud.coffee
class Loud(object):
    '''
    Learns and repeats LOUD MESSAGES!

    To add new LOUDs
      SAY SOMETHING F*@CK!N% LOUDLY

    To remove a LOUD
      .loud forget SOMETHING LOUD
    '''

    log = getLogger('Loud')
    regex = re.compile(r'^\s*(?P<loud>[A-Z"][A-Z0-9 .,\'"()\?!&%$#@+-]+)$')

    def config(self):
        return {'commands': ('loud',), 'messages': True}

    def command(self, context, text, **kwargs):
        if text.startswith('forget '):
            text = text.replace('forget ', '', 1).upper()
            try:
                shout = Shout.objects.get(
                    workspace=context.workspace, text=text
                )
                shout.delete()
                context.say(f"OK. I've removed `{text}` from the list.")
            except Shout.DoesNotExist:
                context.say(f"`{text}` doesn't appear in my list to begin with")
            return

        context.say(f'Unrecognized sub-command `{text}`')

    @exclude_private
    def message(self, context, text, **kwargs):
        match = self.regex.match(text)
        if match:
            # there's a loud in there
            loud = match.group('loud')
            self.log.debug('message: text=%s, match=%s', text, loud)
            # store it if it's new
            Shout.objects.get_or_create(workspace=context.workspace, text=loud)
            # Pick a uniformly random shout for this workspace.
            # get_or_create above guarantees count >= 1.
            # Efficiency: the workspace FK carries a DB index (Django default),
            # so count() is an index range-scan and the offset fetch walks at
            # most N rows in that index — both bounded by a single workspace's
            # shout count, which is small in practice.  Uniform distribution is
            # preserved (no gap-bias from random-id tricks).
            ws_shouts = Shout.objects.filter(workspace=context.workspace)
            count = ws_shouts.count()
            shout = ws_shouts.order_by('id')[randrange(0, count)]
            self.log.debug('message: count=%d, shout=%s', count, shout)
            if shout:
                # we found something say it
                context.say(shout.text)


Registry.register_handler(Loud())
