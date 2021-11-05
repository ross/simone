from random import choice
from simone.handlers import Registry


class TrashTalk(object):
    '''
    Responses to insults, etc.
    '''

    YOU_ARE_A = (
        'I know you are, but what am I?',
        'https://c.tenor.com/48CCVlHm2WEAAAAM/reasons-wrong.gif',
        'https://c.tenor.com/x5WdBoFGX28AAAAC/superstar-im-rubber-and-you-are-glue.gif',
        'https://img.buzzfeed.com/buzzfeed-static/static/2016-08/2/17/asset/buzzfeed-prod-fastlane03/anigif_sub-buzz-19700-1470172352-2.gif',
        'https://img.buzzfeed.com/buzzfeed-static/static/2019-04/4/17/asset/buzzfeed-prod-web-05/anigif_sub-buzz-29277-1554412183-1.gif',
        'https://thumbs.gfycat.com/UnlinedIncomparableBluetonguelizard-max-1mb.gif',
        'https://user-images.githubusercontent.com/12789/140376756-ea0d96b9-6c65-42d5-8688-b4613a7871ec.gif',
    )

    def config(self):
        return {'commands': ("you're a", 'you are a', 'you smell', 'you stink')}

    def help_supress(self, command):
        return True

    def command(self, context, command, text, sender, **kwargs):
        if command in ('you smell', 'you stink'):
            mention = context.user_mention(sender)
            context.say(
                f'Look at this picture of {mention} I found https://i.imgflip.com/fxhda.jpg'
            )
        if command in ("you're a", 'your are a'):
            context.say(choice(self.YOU_ARE_A))


Registry.register_handler(TrashTalk())
