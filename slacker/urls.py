from django.http import HttpRequest
from django.views.decorators.csrf import csrf_exempt
from slack_bolt.adapter.django import SlackRequestHandler

from .listeners import SlackListener


class Dispatcher(object):
    pass


dispatcher = Dispatcher()
listener = SlackListener(dispatcher)
handler = SlackRequestHandler(app=listener.app)


@csrf_exempt
def slack_events_handler(request: HttpRequest):
    return handler.handle(request)
