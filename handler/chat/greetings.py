from django.conf import settings

from simone.handlers import Registry


class Greetings(object):
    def __init__(self, channel_names):
        self.channel_names = channel_names

    def config(self):
        return {'added': True}

    def added(self, context, inviter, **kwargs):
        if context.channel_name in self.channel_names:
            texts = []
            if inviter:
                mention = context.user_mention(inviter)
                texts.append(
                    f'Thanks for the invite {mention}! :wave: everyone'
                )
            else:
                texts.append(':wave: everyone!')
            me = context.user_mention(context.bot_user_id)
            texts += [
                f"I'm {me}. I can do a handful of things currently and I'm always learning to do more",
                'You can type `.help` to get a list of commands and `.help <command>` to get more information about a specific command',
                "If there's something you'd like me to be able to do you can file an issue, or better yet a PR, at https://github.com/ross/simone",
            ]
            context.converse(texts)


channel_names = getattr(settings, 'GREETINGS_CHANNELS', ['greetings'])
Registry.register_handler(Greetings(channel_names))
