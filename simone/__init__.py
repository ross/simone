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

        # TODO: queue things here and process them in a worker pool...

        if event.text.startswith('.'):
            # TODO: allow other whitespace
            name, args = event.text[1:].split(' ', 1)
            self.logger.debug('event:   searching commands, name=%s', name)
            for command in self.commands:
                if name == command.NAME:
                    self.logger.debug('event:     match, command=%s', command)
                    # TODO: built-in arg parsing, if so maybe replace this...
                    if args.startswith('help'):
                        command.help(event)
                    else:
                        command.handle(event)
                    return
            self.logger.debug('event:   nothing interested')
            return

        # TODO: fuzzy/nlp matching
        # TODO: did you mean...
        # TODO: certainty required & quality of matching
        # TODO: acl's
        # TODO: translation support
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
