from django.utils.module_loading import autodiscover_modules
from functools import partial, wraps
from logging import getLogger

from requests import Session

from .context import ChannelType


def only_channel_types(_func=None, channel_types={ChannelType.PUBLIC}):
    def decorate(func):
        @wraps(func)
        def wrap(self, context, command, dispatcher, **kwargs):
            if context.channel_type not in channel_types:
                context.say(
                    f'Sorry, `{dispatcher.LEADER}{command}` cannot be run here'
                )
                return
            return func(
                self, context, command=command, dispatcher=dispatcher, **kwargs
            )

        return wrap

    if _func is None:
        return decorate
    else:
        return decorate(_func)


only_public = only_channel_types


def exclude_channel_types(_func=None, channel_types={ChannelType.DIRECT}):
    def decorate(func):
        @wraps(func)
        def wrap(self, context, command, dispatcher, **kwargs):
            if context.channel_type in channel_types:
                context.say(
                    f'Sorry, `{dispatcher.LEADER}{command}` cannot be run here'
                )
                return
            return func(
                self, context, command=command, dispatcher=dispatcher, **kwargs
            )

        return wrap

    if _func is None:
        return decorate
    else:
        return decorate(_func)


exclude_private = exclude_channel_types


class _Registry(object):
    log = getLogger('Registry')

    handlers = []

    @classmethod
    def autoload(self):
        autodiscover_modules('chat')

    @classmethod
    def register_handler(cls, handler):
        cls.log.info('register_handler: handler=%s', handler)
        cls.handlers.append(handler)


Registry = _Registry()

# A shared requests session that can be used by all handlers to get best
# practices w/o having to deal with the details
session = Session()
session.headers = {'user-agent': 'simone/0.0'}
# shim an default timeout
session.request = partial(session.request, timeout=5)
