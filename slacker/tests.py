from mock import MagicMock
from unittest import TestCase

from .listeners import ChannelType, SenderType, SlackListener


class DummyApp(object):
    def event(self, *args, **kwargs):
        # Won't be using these so just ignore them
        return lambda _: None


class TestSlackListener(TestCase):
    def test_messages(self):
        app = DummyApp()
        dispatcher = MagicMock()
        listener = SlackListener(dispatcher=dispatcher, app=app)

        # message from a user in a public channel
        message = {
            'client_msg_id': '2a549133-9301-4099-9518-dc1e1a7df4ef',
            'type': 'message',
            'text': 'testing',
            'user': 'U01GQ7UFKFX',
            'ts': '1633815504.005800',
            'team': 'T01GZF7DHKN',
            'blocks': [
                {
                    'type': 'rich_text',
                    'block_id': 'PNWH',
                    'elements': [
                        {
                            'type': 'rich_text_section',
                            'elements': [{'type': 'text', 'text': 'testing'}],
                        }
                    ],
                }
            ],
            'channel': 'C01GTHYEU4B',
            'event_ts': '1633815504.005800',
            'channel_type': 'channel',
        }
        dispatcher.reset_mock()
        listener.message(message)
        dispatcher.message.assert_called_once_with(
            text='testing',
            sender='U01GQ7UFKFX',
            sender_type=SenderType.USER,
            channel='C01GTHYEU4B',
            channel_type=ChannelType.PUBLIC,
            team='T01GZF7DHKN',
            thread=None,
            timestamp='1633815504.005800',
        )

        # message from a user in a public channel thread
        message = {
            'client_msg_id': '73da774c-a7e2-42a3-9a09-eb2b0fa3b8b7',
            'type': 'message',
            'text': 'in a thread',
            'user': 'U01GQ7UFKFX',
            'ts': '1633815602.006000',
            'team': 'T01GZF7DHKN',
            'blocks': [
                {
                    'type': 'rich_text',
                    'block_id': 'Yb3X+',
                    'elements': [
                        {
                            'type': 'rich_text_section',
                            'elements': [
                                {'type': 'text', 'text': 'in a thread'}
                            ],
                        }
                    ],
                }
            ],
            'thread_ts': '1633815504.005800',
            'parent_user_id': 'U01GQ7UFKFX',
            'channel': 'C01GTHYEU4B',
            'event_ts': '1633815602.006000',
            'channel_type': 'channel',
        }
        dispatcher.reset_mock()
        listener.message(message)
        dispatcher.message.assert_called_once_with(
            text='in a thread',
            sender='U01GQ7UFKFX',
            sender_type=SenderType.USER,
            channel='C01GTHYEU4B',
            channel_type=ChannelType.PUBLIC,
            team='T01GZF7DHKN',
            thread='1633815504.005800',
            timestamp='1633815602.006000',
        )

        # message from another bot in a public channel
        message = {
            'type': 'message',
            'subtype': 'bot_message',
            'text': 'blah blah blah',
            'ts': '1633888275.007000',
            'bot_id': 'B01GTBL1MJN',
            'channel': 'C01GTHYEU4B',
            'event_ts': '1633888275.007000',
            'channel_type': 'channel',
        }
        dispatcher.reset_mock()
        listener.message(message)
        dispatcher.message.assert_called_once_with(
            text='blah blah blah',
            sender='B01GTBL1MJN',
            sender_type=SenderType.BOT,
            channel='C01GTHYEU4B',
            channel_type=ChannelType.PUBLIC,
            team=None,
            thread=None,
            timestamp='1633888275.007000',
        )

        # message from a user in a private channel
        message = {
            'client_msg_id': 'e8c9c128-d781-4f48-8811-3d3fca32e416',
            'type': 'message',
            'text': 'boo',
            'user': 'U01GQ7UFKFX',
            'ts': '1633816328.000200',
            'team': 'T01GZF7DHKN',
            'blocks': [
                {
                    'type': 'rich_text',
                    'block_id': 'Tp7',
                    'elements': [
                        {
                            'type': 'rich_text_section',
                            'elements': [{'type': 'text', 'text': 'boo'}],
                        }
                    ],
                }
            ],
            'channel': 'C01UTGR299A',
            'event_ts': '1633816328.000200',
            'channel_type': 'group',
        }
        dispatcher.reset_mock()
        listener.message(message)
        dispatcher.message.assert_called_once_with(
            text='boo',
            sender='U01GQ7UFKFX',
            sender_type=SenderType.USER,
            channel='C01UTGR299A',
            channel_type=ChannelType.PRIVATE,
            team='T01GZF7DHKN',
            thread=None,
            timestamp='1633816328.000200',
        )

    def test_joined_and_left(self):
        app = DummyApp()
        dispatcher = MagicMock()
        listener = SlackListener(dispatcher=dispatcher, app=app)

        listener._auth_info = {'user_id': 'U01V6PW6XDE'}

        # bot added to a public channel
        member_joined_channel = {
            'type': 'member_joined_channel',
            'user': 'U01V6PW6XDE',
            'channel': 'C01GTHYEU4B',
            'channel_type': 'C',
            'team': 'T01GZF7DHKN',
            'inviter': 'U01GQ7UFKFX',
            'event_ts': '1633815284.005500',
        }
        dispatcher.reset_mock()
        listener.member_joined_channel(member_joined_channel)
        dispatcher.added.assert_called_once_with(
            channel='C01GTHYEU4B',
            channel_type=ChannelType.PUBLIC,
            team='T01GZF7DHKN',
            inviter='U01GQ7UFKFX',
            timestamp='1633815284.005500',
        )

        # bot removed from public channel
        message = {
            'type': 'message',
            # TODO: what about if bot leaves on its own
            'text': 'You have been removed from #bot-dev by <@U01GQ7UFKFX>',
            'user': 'USLACKBOT',
            'ts': '1633814854.000100',
            'team': 'T01GZF7DHKN',
            'channel': 'D01UDTE3E8M',
            'event_ts': '1633814854.000100',
            'channel_type': 'im',
        }
        dispatcher.reset_mock()
        listener.message(message)
        dispatcher.removed.assert_called_once_with(
            # TODO: once we map
            # channel='C01GTHYEU4B',
            # channel_type=ChannelType.PUBLIC,
            channel='#bot-dev',
            channel_type=None,
            team='T01GZF7DHKN',
            remover='U01GQ7UFKFX',
            timestamp='1633814854.000100',
        )

        # bot is added to a private channel
        member_joined_channel = {
            'type': 'member_joined_channel',
            'user': 'U01V6PW6XDE',
            'channel': 'C01UTGR299A',
            'channel_type': 'C',
            'team': 'T01GZF7DHKN',
            'inviter': 'U01GQ7UFKFX',
            'event_ts': '1633816538.000800',
        }
        dispatcher.reset_mock()
        listener.member_joined_channel(member_joined_channel)
        dispatcher.added.assert_called_once_with(
            channel='C01UTGR299A',
            # TODO: once it's correct
            # channel_type=ChannelType.PRIVATE,
            channel_type=ChannelType.PUBLIC,
            team='T01GZF7DHKN',
            inviter='U01GQ7UFKFX',
            timestamp='1633816538.000800',
        )

        # bot removed from a private channel
        message = {
            'type': 'message',
            'text': 'You have been removed from #bot-dev-private by <@U01GQ7UFKFX>',
            'user': 'USLACKBOT',
            'ts': '1633816442.000100',
            'team': 'T01GZF7DHKN',
            'channel': 'D01UDTE3E8M',
            'event_ts': '1633816442.000100',
            'channel_type': 'im',
        }
        dispatcher.reset_mock()
        listener.message(message)
        dispatcher.removed.assert_called_once_with(
            # TODO: once we map
            # channel='C01GTHYEU4B',
            # channel_type=ChannelType.PUBLIC,
            channel='#bot-dev-private',
            channel_type=None,
            team='T01GZF7DHKN',
            remover='U01GQ7UFKFX',
            timestamp='1633816442.000100',
        )

        # user joins a public channel
        message = {
            'type': 'message',
            'subtype': 'channel_join',
            'ts': '1633815843.006600',
            'user': 'U01GQ7UFKFX',
            'text': '<@U01GQ7UFKFX> has joined the channel',
            'channel': 'C01GTHYEU4B',
            'event_ts': '1633815843.006600',
            'channel_type': 'channel',
        }
        member_joined_channel = {
            'type': 'member_joined_channel',
            'user': 'U01GQ7UFKFX',
            'channel': 'C01GTHYEU4B',
            'channel_type': 'C',
            'team': 'T01GZF7DHKN',
            'event_ts': '1633815843.006500',
        }
        dispatcher.reset_mock()
        listener.message(message)
        listener.member_joined_channel(member_joined_channel)
        dispatcher.joined.assert_called_once_with(
            joiner='U01GQ7UFKFX',
            channel='C01GTHYEU4B',
            channel_type=ChannelType.PUBLIC,
            team='T01GZF7DHKN',
            # TODO: what about when invited
            inviter=None,
            timestamp='1633815843.006500',
        )
        dispatcher.message.assert_not_called()

        # user leaves a public channel
        member_left_channel = {
            'type': 'member_left_channel',
            'user': 'U01GQ7UFKFX',
            'channel': 'C01GTHYEU4B',
            'channel_type': 'C',
            'team': 'T01GZF7DHKN',
            'event_ts': '1633815668.006400',
        }
        dispatcher.reset_mock()
        listener.member_left_channel(member_left_channel)
        dispatcher.left.assert_called_once_with(
            leaver='U01GQ7UFKFX',
            channel='C01GTHYEU4B',
            channel_type=ChannelType.PUBLIC,
            team='T01GZF7DHKN',
            # TODO: what about when kicked by someone
            kicker=None,
            timestamp='1633815668.006400',
        )
        dispatcher.message.assert_not_called()
