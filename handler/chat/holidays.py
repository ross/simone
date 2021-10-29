from datetime import date
from dateutil.parser import ParserError, parse
import holidays

from simone.handlers import Registry


class Holidays(object):
    '''
    Echo back whatever is said
    '''

    def config(self):
        return {'commands': ('holidays',)}

    def command(self, context, text, **kwargs):
        active = []
        if text:
            try:
                today = parse(text)
            except ParserError:
                context.say(f"Sorry. I'm unable to parse `{text}` into a date")
                return
        else:
            today = date.today()
        for cn in holidays.list_supported_countries():
            if cn == cn.upper():
                # this is an abbr
                continue
            holiday = getattr(holidays, cn)().get(today)
            if holiday:
                active.append(f'{holiday} in {cn}')

        today = today.strftime('%Y-%m-%d')
        if active:
            active = '\n'.join(active)
            context.say(f'{today} is:\n```{active}```')
        else:
            context.say(
                "{today} doesn't appear to be a holiday anywhere I have data for"
            )


Registry.register_handler(Holidays())
