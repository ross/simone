from simone.handlers import Registry


class Echo(object):
    '''
    Echo back whatever is said
    '''

    def config(self):
        return {'commands': ('echo',)}

    def command(self, context, text, **kwargs):
        if text == 'boom':
            raise Exception(text)
        context.say(text)


Registry.register_handler(Echo())
