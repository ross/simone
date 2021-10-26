from logging import getLogger
from random import choice, randint
from word2number.w2n import word_to_num

from simone.handlers import Registry


class Coin(object):
    '''
    Flip a coin

    To flip a coin:
      .flip a coin
    '''

    def config(self):
        return {'commands': ('flip a coin',)}

    def command(self, context, command, text, **kwargs):
        context.say(choice(('The coin landed heads', 'The coin landed tails')))


Registry.register_handler(Coin())


class EightBall(object):
    '''
    Ask the magic 8-ball a question

    To consult the magic 8-ball
      .8-ball [question]
      .eight-ball [question]
    '''

    def config(self):
        return {'commands': ('8-ball', 'eight-ball')}

    def command(self, context, command, text, **kwargs):
        response = choice(
            (
                'It is certain.',
                'It is decidedly so.',
                'Without a doubt.',
                'Yes definitely.',
                'You may rely on it.',
                'As I see it, yes.',
                'Most likely.',
                'Outlook good.',
                'Yes.',
                'Signs point to yes.',
                'Reply hazy, try again.',
                'Ask again later.',
                'Better not tell you now.',
                'Cannot predict now.',
                'Concentrate and ask again.',
                "Don't count on it.",
                'My reply is no.',
                'My sources say no.',
                'Outlook not so good.',
                'Very doubtful.',
            )
        )
        context.say(response)


Registry.register_handler(EightBall())


class Dice(object):
    '''
    To roll a die

    To roll a die
      .roll a die
      .roll a <N> sided die
    '''

    log = getLogger('Dice')

    def config(self):
        return {'commands': ('roll a die', 'roll a')}

    def command(self, context, command, text, **kwargs):
        sides = 6
        if command == 'roll a':
            text = text.replace(' sided die', '')
            # try and get a number of sides from text
            try:
                sides = word_to_num(text)
            except ValueError:
                context.say(f"Sorry I'm not sure how many sides `{text}` is")
                return

        roll = randint(1, sides)
        self.log.debug('command: roll=%d for sides=%d', roll, sides)
        response = f'The die landed {roll}'
        context.say(response)


Registry.register_handler(Dice())
