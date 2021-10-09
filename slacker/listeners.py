from django.conf import settings
from logging import getLogger
from os import environ
from slack_bolt import App


class SlackAdapter(object):
    log = getLogger('SlackAdapter')

    def __init__(self, app):
        self.app = app

        @app.event("message")
        def _wrapper_message(event, *args, **kwargs):
            self.message(event)

        @app.event("member_joined_channel")
        def _wrapper_member_joined(event, *args, **kwargs):
            self.member_joined_channel(event)

        @app.event("member_left_channel")
        def _wrapper_member_left(event, *args, **kwargs):
            self.member_left_channel(event)

    def message(self, event):
        self.log.debug('handle_message: event=%s', event)

    def member_joined_channel(self, event):
        self.log.debug('handle_member_joined_channel: event=%s', event)

    def member_left_channel(self, event):
        self.log.debug('handle_member_left_channel: event=%s', event)


app = App(token=environ["SLACK_BOT_TOKEN"], signing_secret=environ["SLACK_SIGNING_SECRET"], token_verification_enabled=not settings.DEBUG)
adapter = SlackAdapter(app)
