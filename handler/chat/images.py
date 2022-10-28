from logging import getLogger
from os import environ
from random import sample
from time import time

from simone.handlers import Registry, session


# register a token
# curl \
#  -X POST \
#  -H "Content-Type: application/json" \
#  -d '{"name": "Simone", "description": "Powers the .image chatop", "email": "rwmcfa1@gmail.com"}' \
#  "https://api.openverse.engineering/v1/auth_tokens/register/"
# check email to verify ^
class _Client(object):
    log = getLogger('OpenVerse')

    def __init__(self, client_id, client_secret):
        self.log.info('__init__: client_id=%s, client_secret=***', client_id)
        self.client_id = client_id
        self.client_secret = client_secret
        self._access_token = None
        self._expiration = None

    @property
    def access_token(self):
        now = time()
        if self._access_token is None or self._expiration < now:
            self.log.info('access_token: refreshing')
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': 'client_credentials',
            }
            resp = session.post(
                'https://api.openverse.engineering/v1/auth_tokens/token/',
                data=data,
            )
            resp.raise_for_status()
            data = resp.json()
            self._access_token = data['access_token']
            self._expiration = now + data['expires_in']
        return self._access_token

    def image_search(self, q):
        self.log.debug('image_search: q="%s"', q)
        # we'll ask for 100 results and choose 5 random ones to use
        params = {'q': q, 'page_size': 100}
        headers = {
            'authorization': f'Bearer {self.access_token}',
            'content-type': 'application/json',
        }
        # this api can be a bit slow so use our own timeout
        resp = session.get(
            'http://api.openverse.engineering/v1/images/',
            params=params,
            timeout=20,
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()
        return data['results']


_client = _Client(
    environ['OPENVERSE_CLIENT_ID'], environ['OPENVERSE_CLIENT_SECRET']
)


class Images(object):
    '''
    Images of a subject of your choice

    To get a random image for a subject
      .image <subject>

    To get image bombed with random images for a subject
      .image bomb <subject>
    '''

    URL = 'https://api.creativecommons.engineering/v1/images'

    def config(self):
        return {'commands': ('image', 'image bomb')}

    def command(self, context, command, text, **kwargs):
        results = _client.image_search(text)
        count = 5 if 'bomb' in command else 1
        sampled = sample(results, min(count, len(results)))
        context.converse([f'<{s["url"]}|{s["title"]}>' for s in sampled])


Registry.register_handler(Images())


class Kittens(Images):
    '''
    Kitten images for all the cat lovers

    To get a random of a kitten
      .kitten

    To get image bombed with random images of kittens
      .kitten bomb
    '''

    def config(self):
        return {'commands': ('kitten', 'kitten bomb')}

    def command(self, context, text, **kwargs):
        super().command(context, text='kitten', **kwargs)


Registry.register_handler(Kittens())


class Puppies(Images):
    '''
    Puppy images for all the cat lovers

    To get a random of a puppy
      .puppy

    To get image bombed with random images of puppies
      .puppy bomb
    '''

    def config(self):
        return {'commands': ('puppy', 'puppy bomb')}

    def command(self, context, text, **kwargs):
        super().command(context, text='puppy', **kwargs)


Registry.register_handler(Puppies())
