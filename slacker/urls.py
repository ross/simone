from django.http import HttpRequest
from django.views.decorators.csrf import csrf_exempt
from slack_bolt.adapter.django import SlackRequestHandler

from .listeners import app

handler = SlackRequestHandler(app=app)


@csrf_exempt
def slack_events_handler(request: HttpRequest):
    return handler.handle(request)
