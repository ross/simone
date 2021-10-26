from simone.handlers import Registry, session


# Port of https://github.com/github/hubot-scripts/blob/master/src/scripts/advice.coffee
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

        if not text:
            return 'Any'

        text = text.lower()
        for keyword, category in self.categories:
            if keyword in text:
                return category

        return None

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

        category = self.find_category(command, text)
        if category is None:
            context.say("Sorry I don't know any jokes about that")
            return
        url = f'{self.BASE_URL}/joke/{category}?safe-mode'
        params = {'lang': 'en'}
        resp = session.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        if data['type'] == 'twopart':
            context.converse((data['setup'], data['delivery']), (5,))
        else:
            context.say(data['joke'])


Registry.register_handler(Joke())
