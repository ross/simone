from simone.handlers import Registry


class Echo(object):
    def config(self):
        return {'commands': ('echo',)}

    def command(self, context, text, **kwargs):
        context.say(text)


Registry.register_handler(Echo())


class Wave(object):
    def config(self):
        return {'messages': True}

    def message(self, context, text, mentions, **kwargs):
        if (
            text.startswith('hi') or text.startswith('hello')
        ) and context.bot_user_id in mentions:
            context.react('wave')


Registry.register_handler(Wave())


class Help(object):
    def config(self):
        return {'commands': ('help',)}

    def command(self, context, text, sender, **kwargs):
        # TODO: text may be the specific command they want help with
        # TODO: search/filter commands
        # TODO: implement something
        context.say('TODO', to_user=sender)


Registry.register_handler(Help())
