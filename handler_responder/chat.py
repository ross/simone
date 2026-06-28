from django.conf import settings
from random import choice, shuffle
from time import time

from simone.handlers import Registry, only_public
from .models import Response, Trigger
from .util import tokenize


class Responder(object):
    '''
    Responds to trigger words or phrases with programmed responses

    Will watch for anyone to say triggers and will pick a random response
    from the linked responses when they do.

    To see all responses
      .when <trigger>

    To add a new response
      .when <trigger> respond <response>

    to remove a response
      .when <trigger> do not respond <response>
    '''

    def __init__(self, cooldown):
        self.cooldown = cooldown
        # {team_id: {tokenized_phrase: trigger_id}}
        # None key is used when workspace is unavailable (pre-migration state).
        self._triggers = {}
        self._last = {}

    def config(self):
        return {'commands': ('when',), 'messages': True}

    @only_public
    def command(self, context, text, mentions, sender, **kwargs):
        if ' do not respond ' in text:
            # removing a response
            phrase, say = [t.strip() for t in text.split(' do not respond ', 1)]
            try:
                trigger = Trigger.objects.get(
                    workspace=context.workspace, phrase=phrase
                )
                response = trigger.responses.get(say=say)
                response.delete()
                if trigger.responses.count() == 0:
                    trigger.delete()
                context.say(
                    f"OK. I won't respond with `{say}` to `{phrase}` anymore."
                )
            except (Response.DoesNotExist, Trigger.DoesNotExist):
                context.say(
                    f"I wouldn't respond with `{say}` to `{phrase}` in the frist place."
                )
            self._invalidate(context)
        elif ' respond ' in text:
            # adding a response
            phrase, say = text.split(' respond ', 1)
            trigger, _ = Trigger.objects.get_or_create(
                workspace=context.workspace, phrase=phrase
            )
            try:
                response = trigger.responses.get(say=say)
            except Response.DoesNotExist:
                response = Response.objects.create(trigger=trigger, say=say)
            context.say(
                f'Got it. When someone says `{phrase}` I might respond `{say}`.'
            )
            self._invalidate(context)
        else:
            # list responses
            phrase = text.strip()
            try:
                trigger = Trigger.objects.get(
                    workspace=context.workspace, phrase=phrase
                )
                responses = '\n--\n'.join(
                    [r.say for r in trigger.responses.all()]
                )
                context.say(
                    f'When someone says `{phrase}` I might respond with ```{responses}```'
                )
            except Trigger.DoesNotExist:
                context.say(f"I don't have any responses for `{text}`")

    def _invalidate(self, context):
        '''Discard the trigger cache for this workspace so it is reloaded next message.'''
        self._triggers.pop(context.team_id, None)

    def _workspace_triggers(self, workspace):
        '''Return (and cache) the trigger map for the given workspace.'''
        team_id = workspace.team_id if workspace else None
        if team_id not in self._triggers:
            self._triggers[team_id] = {
                tokenize(t.phrase): t.id
                for t in Trigger.objects.filter(workspace=workspace)
            }
        return self._triggers[team_id]

    def message(self, context, text, **kwargs):
        if (time() - self._last.get(context.channel_id, 0)) <= self.cooldown:
            # we've responded in this channel recently
            return
        tokens = tokenize(text)
        # shuffle the triggers in case there are multiple matches so that we'll
        # pick a "random" one
        triggers = list(self._workspace_triggers(context.workspace).items())
        shuffle(triggers)
        for phrase, trigger_id in triggers:
            # if the tokenized phrase appears in the tokenized text
            if phrase in tokens:
                # pick a random response
                responses = list(Response.objects.filter(trigger_id=trigger_id))
                if not responses:
                    continue
                response = choice(responses)
                context.say(response.say)
                self._last[context.channel_id] = time()
                break


cooldown = getattr(settings, 'RESPONDER_COOLDOWN', 300)
Registry.register_handler(Responder(cooldown))
