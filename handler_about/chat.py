from simone.dispatcher import Dispatcher
from simone.handlers import Registry, only_public
from .models import Fact


class About(object):
    '''
    Tell people about someone

      To find out about someone
        .who is @handle

      To record a new piece of information about a user
        .@handle is something about them

      To forget a piece of information
        .@handle is not something about them
    '''

    def config(self):
        return {
            'commands': (
                'who is',
                f'{Dispatcher.USER_PLACEHOLDER} is',
                f'{Dispatcher.USER_PLACEHOLDER} is not',
            )
        }

    @only_public
    def command(self, context, command, text, mentions, **kwargs):
        if command == 'who is':
            # show what we've learnt
            if not mentions:
                context.say(
                    f"I can't tell you anything about `{text}`, try an @mention"
                )
                return
            # just use the first mention
            user_id = mentions[0]
            user_mention = context.user_mention(user_id)
            facts = [f.value for f in Fact.objects.filter(user_id=user_id)]
            if not facts:
                context.say(
                    f"I don't know anything about {user_mention}, why don't you tell me somehting"
                )
                return
            facts = ', '.join(facts)
            context.say(f'{user_mention} is {facts}')
        elif command.endswith('is not'):
            # forget something we may have learned in the past
            user_id = mentions[0]
            user_mention = context.user_mention(user_id)
            try:
                fact = Fact.objects.get(user_id=user_id, value=text)
                fact.delete()
                context.say(f"OK. I've forgotten `{text}` about {user_mention}")
            except Fact.DoesNotExist:
                context.say(
                    f"I don't know `{text}` about {user_mention}, it's hard to forget something I don't know."
                )
        else:
            # learn something new
            user_id = mentions[0]
            user_mention = context.user_mention(user_id)
            fact, created = Fact.objects.get_or_create(
                user_id=user_id, value=text
            )
            if not created:
                context.say(f'I alredy know {user_mention} is `{text}`')
                return
            context.say(f'OK. {user_mention} is `{text}`')


Registry.register_handler(About())
