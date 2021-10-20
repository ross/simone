from django.conf import settings
from random import choice, shuffle
from string import punctuation
from time import time

from simone.handlers import Registry, only_public
from .models import Response, Trigger


class Responder(object):
    '''
    Responds to trigger words with programmed responses

    Will watch for anyone to say trigger words and will pick a random response
    from the linked responses when they do.

    To see all responses
      .when <trigger>

    To add a new response
      .when <trigger> respond <response>

    to remove a response
      .when <trigger> do not respond <response>
    '''

    PUNCT_TRANS = str.maketrans('', '', punctuation)

    def __init__(self, cooldown):
        self.cooldown = cooldown
        self._triggers = None
        self._last = {}

    def config(self):
        return {'commands': ('when',), 'messages': True}

    @only_public
    def command(self, context, text, mentions, sender, **kwargs):
        if ' do not respond ' in text:
            # removing a response
            word, say = [t.strip() for t in text.split(' do not respond ', 1)]
            try:
                trigger = Trigger.objects.get(word=word.lower())
                response = trigger.responses.get(say=say)
                response.delete()
                if trigger.responses.count() == 0:
                    trigger.delete()
                context.say(
                    f"OK. I won't respond with `{say}` to `{word}` anymore."
                )
            except (Response.DoesNotExist, Trigger.DoesNotExist):
                context.say(
                    f"I wouldn't respond with `{say}` to `{word}` in the frist place."
                )
            self._triggers = None
        elif ' respond ' in text:
            # adding a response
            word, say = [t.strip() for t in text.split(' respond ', 1)]
            trigger, _ = Trigger.objects.get_or_create(word=word.lower())
            try:
                response = trigger.responses.get(say=say)
            except Response.DoesNotExist:
                response = Response.objects.create(trigger=trigger, say=say)
            context.say(
                f'Got it. When someone says `{word}` I might respond `{say}`.'
            )
            self._triggers = None
        else:
            # list responses
            word = text.strip()
            try:
                trigger = Trigger.objects.get(word=word.lower())
                responses = '\n--\n'.join(
                    [r.say for r in trigger.responses.all()]
                )
                context.say(
                    f'When someone says `{word}` I might respond with ```{responses}```'
                )
            except Trigger.DoesNotExist:
                context.say(f"I don't have any responses for `{text}`")

    @property
    def triggers(self):
        if self._triggers is None:
            self._triggers = {t.word: t.id for t in Trigger.objects.all()}

        return self._triggers

    def message(self, context, text, **kwargs):
        if (time() - self._last.get(context.channel_id, 0)) <= self.cooldown:
            # we've responded in this channel recently
            return
        triggers = self.triggers
        tokens = text.translate(self.PUNCT_TRANS).lower().split(' ')
        # shuffle the tokens in case there are multiple triggers so that we'll
        # pick a "random" one
        shuffle(tokens)
        for token in tokens:
            if token in triggers:
                trigger_id = triggers[token]
                # pick a random response
                response = choice(
                    Response.objects.filter(trigger_id=trigger_id)
                )
                context.say(response.say)
                self._last[context.channel_id] = time()
                break


cooldown = getattr(settings, 'RESPONDER_COOLDOWN', 60)
Registry.register_handler(Responder(cooldown))
