from io import StringIO
from requests import Session
from time import sleep

from simone.handlers import Registry


session = Session()
session.headers = {'user-agent': 'simone/0.0'}


class Echo(object):
    '''
    Echo back whatever is said
    '''

    def config(self):
        return {'commands': ('echo',)}

    def command(self, context, text, **kwargs):
        context.say(text)


Registry.register_handler(Echo())


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
        try:
            # try as-is
            handler = dispatcher.commands[text]
            # add the leader
            text = f'{dispatcher.LEADER}{text}'
        except KeyError:
            try:
                # try skipping the leader in case they did `.help .foo`
                handler = dispatcher.commands[text[len(dispatcher.LEADER) :]]
            except KeyError:
                context.say(f'Sorry `{text}` is not a recognized command')
        context.say(f'Help for `{text}`\n```{handler.__doc__}```')

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
                buf.write(self._summarize_command(command, handler, dispatcher))
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


class Joke(object):
    '''
    Tell a joke
    '''

    def config(self):
        # TODO: multi-word commands
        return {'commands': ('joke', 'tell a joke', 'tell me a joke')}

    def command(self, context, **kwargs):
        # TODO: support filtering and such
        resp = session.get('https://v2.jokeapi.dev/joke/Any?lang=en&safe-mode')
        resp.raise_for_status()
        data = resp.json()
        if data['type'] == 'twopart':
            context.say(data['setup'])
            # TODO: figure out a way to make this async
            sleep(5)
            context.say(data['delivery'])
        else:
            context.say(data['joke'])


Registry.register_handler(Joke())


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
