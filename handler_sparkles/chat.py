from io import StringIO

from simone.handlers import Registry, exclude_private
from .models import User


class Sparkles(object):
    '''
    Spread the love

      To give sparkles:
        .sparkle <@user>
        .sparkle <@user> for being a good human being
        .sparkle <@user> and <@other> for being a good human being
        .sparkle <@user>, <@other>, and <@another>

      To see your current sparkle count:
        .sparkles
    '''

    def config(self):
        return {'commands': ('sparkle', 'sparkles')}

    @exclude_private
    def command(self, context, text, mentions, sender, **kwargs):
        if not mentions:
            mention = context.user_mention(sender)
            try:
                user = User.objects.get(team_id=context.team, user_id=sender)
                context.say(
                    f'{mention} you have {user.sparkles} :sparkles: :tada:'
                )
            except User.DoesNotExist:
                context.say(f"{mention} you don't have any :sparkles: yet")
            return
        elif sender in mentions:
            mention = context.user_mention(sender)
            context.say(f"Nice try {mention}, you can't :sparkle: yourself")
            return

        buf = StringIO()
        if ' for ' in text:
            buf.write('Sparkling ')
            buf.write(text)
            buf.write('\n')

        for user_id in mentions:
            try:
                user = User.objects.get(team_id=context.team, user_id=user_id)
                # We're in a transation so no need to do an F() + 1
                user.sparkles = user.sparkles + 1
                user.save()
            except User.DoesNotExist:
                user = User.objects.create(
                    team_id=context.team, user_id=user_id, sparkles=1
                )

            buf.write(':tada: ')
            buf.write(context.user_mention(user_id))
            buf.write(' has ')
            buf.write(str(user.sparkles))
            buf.write(' :sparkles:s\n')

        context.say(buf.getvalue())


Registry.register_handler(Sparkles())
