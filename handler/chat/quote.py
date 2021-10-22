from simone.handlers import Registry, session


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
