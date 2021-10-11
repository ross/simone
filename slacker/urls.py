from django.http import HttpRequest
from django.views.decorators.csrf import csrf_exempt
from pprint import pprint
from slack_bolt.adapter.django import SlackRequestHandler

from .listeners import SlackListener


class Dispatcher(object):
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


dispatcher = Dispatcher()
listener = SlackListener(dispatcher)
handler = SlackRequestHandler(app=listener.app)


@csrf_exempt
def slack_events_handler(request: HttpRequest):
    return handler.handle(request)
