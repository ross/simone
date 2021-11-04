from io import StringIO

from simone.handlers import Registry


class Help(object):
    '''
    Display a list of supported commands and get usage information.

    To display the list of commands:
      .help

    To get the usage for a specific command:
      .help <command-name>

    To filter commands to those that include a phrase in their name or help
      .help | <word or phrase>
    '''

    def __init__(self):
        self._command_list = None

    def config(self):
        return {'commands': ('help',)}

    def help_command(self, context, text, dispatcher):
        if text.startswith(dispatcher.LEADER):
            text = text[len(dispatcher.LEADER) :]
        _, handler, _, _ = dispatcher.find_handler(text)
        if handler:
            context.say(f'Help for `{text}`\n```{handler.__doc__}```')
        else:
            context.say(f'Sorry `{text}` is not a recognized command')

    def _summarize_command(self, command, handler, dispatcher):
        try:
            short = handler.__doc__.split('\n')[1].strip()
            maybe_short = f' - {short}'
        except AttributeError:
            maybe_short = ''
        return f'  {dispatcher.LEADER}{command}{maybe_short}\n'

    def list_commands(self, context, dispatcher):
        if self._command_list is None:
            buf = StringIO()
            buf.write('Supported commands:\n```')
            for command, handler in sorted(dispatcher.commands.items()):
                try:
                    supress = handler.help_supress(command)
                except AttributeError:
                    supress = False
                if not supress:
                    buf.write(
                        self._summarize_command(command, handler, dispatcher)
                    )
            buf.write('```')
            self._command_list = buf.getvalue()

        context.say(self._command_list)

    def search_commands(self, context, text, dispatcher):
        text = text[1:].strip()
        buf = StringIO()
        buf.write('Commands matching `')
        buf.write(text)
        buf.write('`:\n```')
        for command, handler in sorted(dispatcher.commands.items()):
            if text in command or text in handler.__doc__:
                buf.write(self._summarize_command(command, handler, dispatcher))
                # we want to include this one
        buf.write('```')
        context.say(buf.getvalue())

    def command(self, context, text, dispatcher, **kwargs):
        if text:
            if text.startswith('|'):
                self.search_commands(context, text, dispatcher)
            else:
                self.help_command(context, text, dispatcher)
        else:
            self.list_commands(context, dispatcher)


Registry.register_handler(Help())
