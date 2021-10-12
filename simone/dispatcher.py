from pprint import pprint

from slacker.listeners import SlackListener


class Echo(object):
    def config(self):
        return {'commands': ('echo',)}

    def command(self, context, text, channel, thread, **kwargs):
        context.say(text, channel, thread=thread)


class Dispatcher(object):
    def __init__(self):
        self.listeners = [SlackListener(self)]

        handlers = [Echo()]
        self.handlers = handlers
        commands = {}
        for handler in handlers:
            config = handler.config()
            for command in config.get('commands', []):
                commands[command] = handler

        self.commands = commands

    def urlpatterns(self):
        return sum([l.urlpatterns() for l in self.listeners], [])

    def added(*args, **kwargs):
        pprint({'type': 'added', 'args': args, 'kwargs': kwargs})

    def command(self, context, command, channel, *args, **kwargs):
        try:
            command = self.commands[command]
        except KeyError:
            # TODO: translation support?
            # TODO: respond private or in thread?
            # TODO: generic formatting of text or just adopt slack's?
            # TODO: levenshtein distance to find similar commands?
            context.say(
                f'Sorry `{command}` is not a recognized command', channel
            )
        else:
            # TODO: we should catch and log all exceptions down here
            command.command(context, channel=channel, *args, **kwargs)

    def edit(*args, **kwargs):
        pprint({'type': 'edit', 'args': args, 'kwargs': kwargs})

    def joined(*args, **kwargs):
        pprint({'type': 'joined', 'args': args, 'kwargs': kwargs})

    def left(*args, **kwargs):
        pprint({'type': 'left', 'args': args, 'kwargs': kwargs})

    def message(*args, **kwargs):
        pprint({'type': 'message', 'args': args, 'kwargs': kwargs})

    def removed(*args, **kwargs):
        pprint({'type': 'removed', 'args': args, 'kwargs': kwargs})
