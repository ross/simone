from random import sample

from simone.handlers import Registry, session


# TODO: support auth_tokens
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
        # we'll ask for 100 results and choose 5 random ones to use
        params = {'q': text, 'page_size': 100}
        # this api can be a bit slow so use our own timeout
        resp = session.get(
            self.URL,
            params=params,
            timeout=20,
            headers={'content-type': 'application/json'},
        )
        resp.raise_for_status()
        data = resp.json()
        results = data['results']
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
