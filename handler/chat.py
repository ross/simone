from django.conf import settings
from functools import partial
from io import StringIO
from os import environ
from requests import Session
from time import sleep

from simone.handlers import Registry


session = Session()
session.headers = {'user-agent': 'simone/0.0'}
# shim an default timeout
session.request = partial(session.request, timeout=5)


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


class Greetings(object):
    def __init__(self, channel_names):
        self.channel_names = channel_names

    def config(self):
        return {'added': True}

    def added(self, context, inviter, **kwargs):
        if context.channel_name in self.channel_names:
            if inviter:
                mention = context.user_mention(inviter)
                context.say(f'Thanks for the invite {mention}! :wave: everyone')
            else:
                context.say(':wave: everyone!')
            sleep(2)
            me = context.user_mention(context.bot_user_id)
            context.say(
                f"I'm {me}. I can do a handful of things currently and I'm always learning to do more every day"
            )
            sleep(3)
            context.say(
                'You can type `.help` to get a list of commands and `.help <command>` to get more information about a specific command'
            )
            sleep(1.5)
            context.say(
                "If there's something you'd like me to be able to do you can file an issue, or better yet a PR, at https://github.com/ross/simone"
            )


channel_names = getattr(settings, 'GREETINGS_CHANNELS', ['greetings'])
Registry.register_handler(Greetings(channel_names))


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

    To get a random joke
      .joke
      .tell a joke
      .tell me a joke

    To get a random joke from a specific category
      .joke about <category>
      .tell a joke about <category>
      .tell me a joke about <category>

    To get a random punny joke
      .pun
      .pun me

    To get a list of supported categories
      .joke categories
    '''

    BASE_URL = 'https://v2.jokeapi.dev'

    def __init__(self):
        self._categories = None

    def config(self):
        return {'commands': ('joke', 'pun', 'tell a joke', 'tell me a joke')}

    @property
    def categories(self):
        if self._categories is None:
            resp = session.get(f'{self.BASE_URL}/categories')
            resp.raise_for_status()
            data = resp.json()

            categories = (
                [(c.lower(), c) for c in data['categories']]
                + [
                    (a['alias'].lower(), a['resolved'])
                    for a in data['categoryAliases']
                ]
                + [
                    ('anything', 'Any'),
                    ('coding', 'Programming'),
                    ('something', 'Any'),
                    ('tech', 'Programming'),
                ]
            )

            self._categories = categories

        return self._categories

    def find_category(self, command, text):
        if command == 'pun':
            return 'Pun'

        text = text.lower()
        for keyword, category in self.categories:
            if keyword in text:
                return category

        return 'Any'

    def command(self, context, command, text, **kwargs):
        if 'categories' in text:
            categories = ', '.join(
                sorted(
                    [
                        f'`{c[0]}`'
                        for c in self.categories
                        if c[0] not in ('any', 'anything', 'something')
                    ]
                )
            )
            context.say(f'I can tell you jokes about {categories}')
            return

        url = f'{self.BASE_URL}/joke/{self.find_category(command, text)}?safe-mode'
        params = {'lang': 'en'}
        resp = session.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        if data['type'] == 'twopart':
            context.say(data['setup'])
            sleep(5)
            context.say(data['delivery'])
        else:
            context.say(data['joke'])


Registry.register_handler(Joke())


class Ping(object):
    '''
    Ping...Pong
    '''

    def config(self):
        return {'commands': ('ping',)}

    def command(self, context, **kwargs):
        context.say('pong')


Registry.register_handler(Ping())


class Quote(object):
    '''
    Grab a quote

    To get a random quote
      .quote

    To get a random quote by a specific author
      .quote by <author>
      .quote by <author1>|<author2>

    To get a random quote about a specific subject
      .quote about <tag>
      .quote about <tag1>,<tag2>
      .quote about <tag1>|<tag2>

    To search the list of authors
      .quote authors | <string>

    To get a list of subject tags
      .quote tags
    '''

    BASE_URL = 'https://api.quotable.io'

    def __init__(self):
        self._authors = None
        self._tags = None

    @property
    def authors(self):
        if self._authors is None:
            url = f'{self.BASE_URL}/authors'
            params = {'limit': 100, 'page': 0}
            more = True
            authors = {}
            while more:
                resp = session.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                for author in data['results']:
                    authors[author['name']] = author['name'].lower()
                params['page'] += 1
                more = data['totalCount'] > len(authors)

            self._authors = authors

        return self._authors

    @property
    def tags(self):
        if self._tags is None:
            url = f'{self.BASE_URL}/tags'
            resp = session.get(url)
            resp.raise_for_status()
            self._tags = ', '.join([f'`{t["name"]}`' for t in resp.json()])
        return self._tags

    def config(self):
        return {'commands': ('quote',)}

    def command(self, context, command, text, **kwargs):
        params = {}
        if text == 'tags':
            context.say(f'The following tags are supported: {self.tags}')
            return
        elif text.startswith('authors |'):
            query = text.split('|', 1)[1].lower()
            authors = ', '.join(
                [f'`{n}`' for n, l in self.authors.items() if query in l]
            )
            context.say(f'The following authors match: {authors}')
            return

        by_i = text.find('by ')
        about_i = text.find('about ')
        if by_i > -1 and about_i > -1:
            # both author and tag
            if by_i < about_i:
                # by came first
                params['tags'] = text[about_i + 5 :].strip()
                params['author'] = text[by_i + 3 : about_i].strip()
            else:
                # about came first
                params['author'] = text[by_i + 3 :].strip()
                params['tags'] = text[about_i + 5 : by_i].strip()
        elif by_i > -1:
            params['author'] = text[by_i + 3 :].strip()
        elif about_i > -1:
            params['tags'] = text[about_i + 5 :].strip()

        url = f'{self.BASE_URL}/random'
        resp = session.get(url, params=params)
        if resp.status_code == 404:
            context.say(f'No quotes matched `{text}`')
            return
        resp.raise_for_status()
        data = resp.json()
        context.say(f'{data["content"]} - {data["author"]}')


Registry.register_handler(Quote())


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


class Weather(object):
    '''
    Get the current weather

    To get the weather for a city
      .weather <city name>
    '''

    URL = 'https://api.openweathermap.org/data/2.5/weather'

    def __init__(self, app_id):
        self.app_id = app_id

    def config(self):
        return {'commands': ('weather',)}

    def _weather_icon(self, data):
        try:
            weather = data['weather'][0]
            icon = weather['icon']
            desc = f'{weather["main"]} - {weather["description"]}'
            return f'<https://openweathermap.org/img/wn/{icon}@2x.png|{desc}>'
        except (IndexError, KeyError):
            return ''

    def command(self, context, text, **kwargs):
        # TODO: support C?
        params = {'q': text, 'appid': self.app_id, 'units': 'imperial'}
        resp = session.get(self.URL, params=params)
        if resp.status_code == 404:
            # unknown location/city
            context.say(f"Sorry. I wasn't able to find weather for `{text}`")
            return
        resp.raise_for_status()
        data = resp.json()
        main = data['main']
        temp = main['temp']
        feels_like = main['feels_like']
        humidity = main['humidity']
        weather_icon = self._weather_icon(data)
        context.say(
            f'Current weather for `{text}`: {temp}F, feels like {feels_like}F. {humidity}% humidity. {weather_icon}'
        )


app_id = environ['OPEN_WEATHER_MAP_APP_ID']
Registry.register_handler(Weather(app_id))
