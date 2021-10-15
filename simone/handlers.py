from django.utils.module_loading import autodiscover_modules


class _Registry(object):
    handlers = []

    @classmethod
    def autoload(self):
        autodiscover_modules('chat')

    @classmethod
    def register_handler(cls, handler):
        cls.handlers.append(handler)


Registry = _Registry()
