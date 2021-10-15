from simone.handlers import Registry
from .models import Item


class Memory(object):
    def config(self):
        return {'commands': ('rem', 'remember', 'forget')}

    def command(self, context, command, text, **kwargs):
        if command in ('rem', 'remember'):
            if ' is ' in text:
                # we're recording
                key, value = text.split(' is ', 1)
                item, _ = Item.objects.update_or_create(
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
