from pprint import pprint

from slacker.listeners import SlackListener


class Dispatcher(object):
    def __init__(self):
        self.listeners = [SlackListener(self)]

    def urlpatterns(self):
        return sum([l.urlpatterns() for l in self.listeners], [])

    def added(*args, **kwargs):
        pprint({'type': 'added', 'args': args, 'kwargs': kwargs})

    def command(*args, **kwargs):
        pprint({'type': 'command', 'args': args, 'kwargs': kwargs})

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
