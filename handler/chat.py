from io import StringIO

from simone.handlers import Registry


class Echo(object):
    '''
    Echo back whatever is said
    '''

    def config(self):
        return {'commands': ('echo',)}

    def command(self, context, text, **kwargs):
        context.say(text)


Registry.register_handler(Echo())


class Wave(object):
    '''
    Adds a :wave: emoji to messages that say hi to the bot user.
    '''

    def config(self):
        return {'messages': True}

    def message(self, context, text, mentions, **kwargs):
        if (
            text.startswith('hi') or text.startswith('hello')
        ) and context.bot_user_id in mentions:
            context.react('wave')


Registry.register_handler(Wave())


class Help(object):
    '''
    Display a list of supported commands
    '''

    def config(self):
        return {'commands': ('help',)}

    def help_command(self, context, text, dispatcher):
        for command, handler in sorted(dispatcher.commands.items()):
            if command == text:
                context.say(f'Help for `.{text}`\n```{handler.__doc__}```')
                return
        context.say(f'Sorry `{text}` is not a recognized command')

    def list_commands(self, context, dispatcher):
        buf = StringIO()
        buf.write('Supported commands:\n```')
        # TODO: cache
        for command, handler in sorted(dispatcher.commands.items()):
            buf.write('  .')
            buf.write(command)
            try:
                short = handler.__doc__.split('\n')[1].strip()
                buf.write(' - ')
                buf.write(short)
            except AttributeError:
                pass
            buf.write('\n')
        buf.write('```')

        context.say(buf.getvalue())

    def command(self, context, text, dispatcher, **kwargs):
        if text:
            self.help_command(context, text, dispatcher)
        else:
            # TODO: search/filter commands
            self.list_commands(context, dispatcher)


Registry.register_handler(Help())
