#
#
#

from logging import getLogger
from pprint import pprint


class Simone(object):
    logger = getLogger('Simone')

    def __init__(self, commands, interactions, adapter):
        self.logger.info('__init__: commands=***, interactions=***, '
                         'adapter=%s', adapter)
        self.adapter = adapter

        self.commands = commands
        self.interactions = interactions

        adapter.register(self)

    def event(self, event):
        self.logger.debug('event: event=%s', event)

        # TODO: fuzzy/nlp matching
        # TODO: certainty required & quality of matching
        # TODO: acl's
        interested = []
        for interaction in self.interactions:
            self.logger.debug('event:   interaction=%s', interaction)
            event_type_wanted = getattr(interaction, 'EVENT_TYPE', None)
            if event_type_wanted is not None and \
                   not isinstance(event, event_type_wanted):
                self.logger.debug('event:     wrong event_type')
                # interaction has a event type and it's not a match, next...
                continue
            trigger = getattr(interaction, 'TRIGGER', None)
            if trigger is not None and trigger != event.text:
                self.logger.debug('event:     no trigger match')
                # interaction has a trigger and it's not a match, next ...
                continue
            # match
            interested.append(interaction)

        self.logger.debug('event:   interested=%s', interested)
        if not interested:
            self.logger.debug('event:   nothing interested')
            return False

        # TODO: multiple and pick a winner? multiple and fire? 
        return interested[0].handle(event)

    # TODO: convert this into an interaction
    def new_channel(self, channel, invited_by, message):
        self.adapter.say('Thanks for the invite <user:invited_by>! '
                         'Hello everyone :wave:', {
                             'invited_by': invited_by,
                        })
