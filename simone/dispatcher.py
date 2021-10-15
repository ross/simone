from pprint import pprint

from handler_memory.handlers import Memory
from slacker.listeners import SlackListener


class Echo(object):
    def config(self):
        return {'commands': ('echo',)}

    def command(self, context, text, **kwargs):
        context.say(text)


class Wave(object):
    def config(self):
        return {'messages': True}

    def message(self, context, text, mentions, **kwargs):
        if (
            text.startswith('hi') or text.startswith('hello')
        ) and context.bot_user_id in mentions:
            context.react('wave')


class Help(object):
    def config(self):
        return {'commands': ('help',)}

    def command(self, context, text, sender, **kwargs):
        # TODO: text may be the specific command they want help with
        # TODO: search/filter commands
        # TODO: implement something
        context.say('TODO', to_user=sender)


class Dispatcher(object):
    def __init__(self):
        self.listeners = [SlackListener(self)]

        handlers = [Echo(), Help(), Memory(), Wave()]
        self.handlers = handlers
        messages = []
        commands = {}
        for handler in handlers:
            config = handler.config()
            for command in config.get('commands', []):
                commands[command] = handler
            if config.get('messages', False):
                messages.append(handler)

        self.commands = commands
        self.messages = messages

    def urlpatterns(self):
        return sum([l.urlpatterns() for l in self.listeners], [])

    def added(*args, **kwargs):
        pprint({'type': 'added', 'args': args, 'kwargs': kwargs})

    def command(self, context, command, **kwargs):
        try:
            handler = self.commands[command]
        except KeyError:
            # TODO: translation support?
            # TODO: respond private or in thread?
            # TODO: generic formatting of text or just adopt slack's?
            # TODO: levenshtein distance to find similar commands?
            context.say(f'Sorry `{command}` is not a recognized command')
        else:
            # TODO: we should catch and log all exceptions down here
            handler.command(context, command=command, **kwargs)

    def edit(*args, **kwargs):
        pprint({'type': 'edit', 'args': args, 'kwargs': kwargs})

    def joined(*args, **kwargs):
        pprint({'type': 'joined', 'args': args, 'kwargs': kwargs})

    def left(*args, **kwargs):
        pprint({'type': 'left', 'args': args, 'kwargs': kwargs})

    def message(self, *args, **kwargs):
        pprint({'type': 'left', 'args': args, 'kwargs': kwargs})
        for handler in self.messages:
            handler.message(*args, **kwargs)

    def removed(*args, **kwargs):
        pprint({'type': 'removed', 'args': args, 'kwargs': kwargs})
