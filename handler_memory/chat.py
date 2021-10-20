from io import StringIO

from simone.handlers import Registry, only_public
from .models import Item


class Memory(object):
    '''
    Store and retrieve information

      To record a piece of information:
        .rem|.remember <the thing> is <remembered info>

      To recall a piece of information
        .rem|.remember <the thing>

      To forget a piece of information
        .forget <the thing>
    '''

    def config(self):
        return {'commands': ('rem', 'remember', 'forget')}

    @only_public
    def command(self, context, command, text, **kwargs):
        if command in ('rem', 'remember'):
            if text[0] == '|':
                # search
                text = text.split('|', 1)[1].strip()
                items = Item.objects.filter(
                    team_id=context.team, key__icontains=text
                )[:25]
                if items:
                    buf = StringIO()
                    buf.write('You might be looking for one of these:\n```')
                    for item in items:
                        buf.write('  ')
                        buf.write(item.key)
                        buf.write('\n')
                    buf.write('```')
                    msg = buf.getvalue()
                else:
                    msg = f"Sorry. I didn't find anything that matches `{text}`"
                context.say(msg)
            elif ' is ' in text:
                # we're recording
                key, value = text.split(' is ', 1)
                try:
                    item = Item.objects.get(team_id=context.team, key=key)
                    context.say(
                        f"Unfortunately, {item.key} is already stored as {item.value}; Try forgetting it first"
                    )
                except Item.DoesNotExist:
                    item = Item.objects.create(
                        team_id=context.team, key=key, value=value
                    )
                    context.say(f"OK. I'll remember {item.key} is {item.value}")
            else:
                try:
                    item = Item.objects.get(team_id=context.team, key=text)
                    context.say(f'{item.key} is {item.value}')
                except Item.DoesNotExist:
                    context.say(
                        f"Sorry. I don't remember anything about {text}"
                    )
        else:  # forget
            try:
                item = Item.objects.get(team_id=context.team, key=text)
                context.say(f"OK. I'll forget that {item.key} was {item.value}")
                item.delete()
            except Item.DoesNotExist:
                context.say(f"Sorry. I don't remember anything about {text}")


Registry.register_handler(Memory())
