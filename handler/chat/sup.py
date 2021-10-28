from simone.handlers import Registry
from random import choice


class Sup(object):
    '''
    Monday morning (US-time) what's everyone been up to message
    '''

    UP_TOS = (
        'I spent most of the weekend reticulating splines',
        'I put some quality time in on my novel',
        'I tweaked my robo investor algorithm 2e12 times',
        'I mostly doomscrolled the news',
        'I updated my dependencies',
        'I read a couple books, took a nap, and rehearsed my one bot play',
    )

    def config(self):
        return {
            'crons': [
                {
                    'listener': 'slack',
                    'channel': 'greetings',
                    'when': '00 13 * * *',
                }
            ]
        }

    def cron(self, context, **kwargs):
        context.converse(
            ['What have you all been up to lately?', choice(self.UP_TOS)]
        )


Registry.register_handler(Sup())
