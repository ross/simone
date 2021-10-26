from random import choice

from simone.handlers import Registry, session


class Advice(object):
    '''
    Get sage advice on the subject of your choosing

    To get random advice
      .advice

    To get advice on a specific subject
      @simone what should i do about [thing]
      @simone what do you think about [thing]
      @simone what how do you handle [thing]
    '''

    BASE_URL = 'https://api.adviceslip.com/advice'

    def __init__(self):
        self._categories = None

    def config(self):
        return {
            'commands': (
                'advice',
                'what should i do about',
                'what do you think about',
                'how do you handle',
            )
        }

    def random(self):
        resp = session.get(self.BASE_URL)
        resp.raise_for_status()
        data = resp.json()
        return data['slip']['advice']

    def on_subject(self, subject):
        url = f'{self.BASE_URL}/search/{subject}'
        resp = session.get(url)
        resp.raise_for_status()
        data = resp.json()
        slips = [s['advice'] for s in data.get('slips', [])]
        if not slips:
            return "Sorry, I've got nothing on that subject"
        return choice(slips)

    def command(self, context, command, text, **kwargs):
        if command == 'advice' or not text:
            slip = self.random()
        else:
            slip = self.on_subject(text)

        context.say(slip)


Registry.register_handler(Advice())
