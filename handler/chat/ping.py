from simone.handlers import Registry


class Ping(object):
    '''
    Ping...Pong
    '''

    def config(self):
        return {'commands': ('ping',)}

    def command(self, context, **kwargs):
        context.say('pong')


Registry.register_handler(Ping())
