from pprint import pprint

from slacker.listeners import SlackListener


class Echo(object):
    def config(self):
        return {'commands': ('echo',)}

    def command(self, context, text, channel, thread, **kwargs):
        context.say(text)


class Memory(object):
    def __init__(self):
        # TODO: this should be db backed
        self.memory = {}

    def config(self):
        return {'commands': ('rem', 'remember', 'forget')}

    def command(self, context, command, text, channel, thread, **kwargs):
        if command in ('rem', 'remember'):
            if ' is ' in text:
                # we're recording
                what, about = text.split(' is ', 1)
                self.memory[what] = about
                context.say(f"OK. I'll remember {what} is {about}")
            elif text in self.memory:
                context.say(f'{text} is {self.memory[text]}')
            else:
                context.say(f"Sorry. I don't remember anything about {text}")
        else:  # forget
            if text in self.memory:
                what = self.memory.pop(text)
                context.say(f"OK. I'll forget that {text} was {what}")
            else:
                context.say(f"Sorry. I don't remember anything about {text}")


class Context(object):
    def __init__(self, listener, channel, thread):
        self.listener = listener
        self.channel = channel
        self.thread = thread

    def say(self, text, thread=None):
        thread = thread or self.thread
        self.listener.say(text, self.channel, thread)


class Dispatcher(object):
    def __init__(self):
        self.listeners = [SlackListener(self)]

        handlers = [Echo(), Memory()]
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

    def command(self, listener, command, channel, thread, *args, **kwargs):
        context = Context(listener, channel, thread=thread)
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
            handler.command(
                context,
                command=command,
                channel=channel,
                thread=thread,
                *args,
                **kwargs,
            )

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
