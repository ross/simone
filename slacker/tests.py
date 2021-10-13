from mock import MagicMock, patch
from django.test import TestCase

from simone.context import ChannelType
from .models import Channel
from .listeners import SenderType, SlackContext, SlackListener


class DummyApp(object):
    def event(self, *args, **kwargs):
        # Won't be using these so just ignore them
        return lambda _: None


class TestSlackListener(TestCase):
    def test_messages(self):
        app = DummyApp()
        dispatcher = MagicMock()
        listener = SlackListener(dispatcher=dispatcher, app=app)
        listener._auth_info = {'user_id': 'U01GQ7UFKFX'}

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
            context=SlackContext(
                app=app,
                channel='C01GTHYEU4B',
                channel_type=ChannelType.PUBLIC,
                team='T01GZF7DHKN',
                thread=None,
                timestamp='1633815504.005800',
            ),
            text='testing',
            sender='U01GQ7UFKFX',
            sender_type=SenderType.USER,
            mentions=[],
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
            context=SlackContext(
                app=app,
                channel='C01GTHYEU4B',
                channel_type=ChannelType.PUBLIC,
                team='T01GZF7DHKN',
                thread='1633815504.005800',
                timestamp='1633815602.006000',
            ),
            text='in a thread',
            sender='U01GQ7UFKFX',
            sender_type=SenderType.USER,
            mentions=[],
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
            context=SlackContext(
                app=app,
                channel='C01GTHYEU4B',
                channel_type=ChannelType.PUBLIC,
                team=None,
                thread=None,
                timestamp='1633888275.007000',
            ),
            text='blah blah blah',
            sender='B01GTBL1MJN',
            sender_type=SenderType.BOT,
            mentions=[],
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
            context=SlackContext(
                app=app,
                channel='C01UTGR299A',
                channel_type=ChannelType.PRIVATE,
                team='T01GZF7DHKN',
                thread=None,
                timestamp='1633816328.000200',
            ),
            text='boo',
            sender='U01GQ7UFKFX',
            sender_type=SenderType.USER,
            mentions=[],
        )

        # message that will be edited
        message = {
            'client_msg_id': 'a3a6ce90-396f-4be7-81c4-bacd4f35b557',
            'type': 'message',
            'text': 'this will be edited',
            'user': 'U01GQ7UFKFX',
            'ts': '1633912633.008700',
            'team': 'T01GZF7DHKN',
            'blocks': [
                {
                    'type': 'rich_text',
                    'block_id': 'PJ95',
                    'elements': [
                        {
                            'type': 'rich_text_section',
                            'elements': [
                                {'type': 'text', 'text': 'this will be edited'}
                            ],
                        }
                    ],
                }
            ],
            'channel': 'C01GTHYEU4B',
            'event_ts': '1633912633.008700',
            'channel_type': 'channel',
        }
        dispatcher.reset_mock()
        listener.message(message)
        dispatcher.message.assert_called_once_with(
            context=SlackContext(
                app=app,
                channel='C01GTHYEU4B',
                channel_type=ChannelType.PUBLIC,
                team='T01GZF7DHKN',
                thread=None,
                timestamp='1633912633.008700',
            ),
            text='this will be edited',
            sender='U01GQ7UFKFX',
            sender_type=SenderType.USER,
            mentions=[],
        )

        # edited version
        message = {
            'type': 'message',
            'subtype': 'message_changed',
            'hidden': True,
            'message': {
                'client_msg_id': 'a3a6ce90-396f-4be7-81c4-bacd4f35b557',
                'type': 'message',
                'text': 'this was edited',
                'user': 'U01GQ7UFKFX',
                'team': 'T01GZF7DHKN',
                'edited': {'user': 'U01GQ7UFKFX', 'ts': '1633912640.000000'},
                'blocks': [
                    {
                        'type': 'rich_text',
                        'block_id': '2X9V',
                        'elements': [
                            {
                                'type': 'rich_text_section',
                                'elements': [
                                    {'type': 'text', 'text': 'this was edited'}
                                ],
                            }
                        ],
                    }
                ],
                'ts': '1633912633.008700',
                'source_team': 'T01GZF7DHKN',
                'user_team': 'T01GZF7DHKN',
            },
            'channel': 'C01GTHYEU4B',
            'previous_message': {
                'client_msg_id': 'a3a6ce90-396f-4be7-81c4-bacd4f35b557',
                'type': 'message',
                'text': 'this will be edited',
                'user': 'U01GQ7UFKFX',
                'ts': '1633912633.008700',
                'team': 'T01GZF7DHKN',
                'blocks': [
                    {
                        'type': 'rich_text',
                        'block_id': 'PJ95',
                        'elements': [
                            {
                                'type': 'rich_text_section',
                                'elements': [
                                    {
                                        'type': 'text',
                                        'text': 'this will be edited',
                                    }
                                ],
                            }
                        ],
                    }
                ],
            },
            'event_ts': '1633912640.008800',
            'ts': '1633912640.008800',
            'channel_type': 'channel',
        }
        dispatcher.reset_mock()
        listener.message(message)
        dispatcher.message.assert_not_called()
        dispatcher.edit.assert_called_once_with(
            context=SlackContext(
                app=app,
                channel='C01GTHYEU4B',
                channel_type=ChannelType.PUBLIC,
                team='T01GZF7DHKN',
                thread=None,
                timestamp='1633912640.008800',
            ),
            text='this was edited',
            previous_text='this will be edited',
            sender='U01GQ7UFKFX',
            sender_type=SenderType.USER,
            previous_timestamp='1633912633.008700',
            mentions=[],
        )

        # message in thread that will be edited
        message = {
            'client_msg_id': 'ec80dd64-441d-4a8c-a7ab-36af9ca04a4d',
            'type': 'message',
            'text': 'this thread message will be edited',
            'user': 'U01GQ7UFKFX',
            'ts': '1633981229.008900',
            'team': 'T01GZF7DHKN',
            'blocks': [
                {
                    'type': 'rich_text',
                    'block_id': 'CnBA',
                    'elements': [
                        {
                            'type': 'rich_text_section',
                            'elements': [
                                {
                                    'type': 'text',
                                    'text': 'this thread message will be edited',
                                }
                            ],
                        }
                    ],
                }
            ],
            'thread_ts': '1633912633.008700',
            'parent_user_id': 'U01GQ7UFKFX',
            'channel': 'C01GTHYEU4B',
            'event_ts': '1633981229.008900',
            'channel_type': 'channel',
        }
        dispatcher.reset_mock()
        listener.message(message)
        dispatcher.message.assert_called_once_with(
            context=SlackContext(
                app=app,
                channel='C01GTHYEU4B',
                channel_type=ChannelType.PUBLIC,
                team='T01GZF7DHKN',
                thread='1633912633.008700',
                timestamp='1633981229.008900',
            ),
            text='this thread message will be edited',
            sender='U01GQ7UFKFX',
            sender_type=SenderType.USER,
            mentions=[],
        )
        # edited version
        message = {
            'type': 'message',
            'subtype': 'message_changed',
            'hidden': True,
            'message': {
                'client_msg_id': 'ec80dd64-441d-4a8c-a7ab-36af9ca04a4d',
                'type': 'message',
                'text': 'this thread message was edited',
                'user': 'U01GQ7UFKFX',
                'team': 'T01GZF7DHKN',
                'edited': {'user': 'U01GQ7UFKFX', 'ts': '1633981255.000000'},
                'blocks': [
                    {
                        'type': 'rich_text',
                        'block_id': 'pndo',
                        'elements': [
                            {
                                'type': 'rich_text_section',
                                'elements': [
                                    {
                                        'type': 'text',
                                        'text': 'this thread message was edited',
                                    }
                                ],
                            }
                        ],
                    }
                ],
                'thread_ts': '1633912633.008700',
                'parent_user_id': 'U01GQ7UFKFX',
                'ts': '1633981229.008900',
                'source_team': 'T01GZF7DHKN',
                'user_team': 'T01GZF7DHKN',
            },
            'channel': 'C01GTHYEU4B',
            'previous_message': {
                'client_msg_id': 'ec80dd64-441d-4a8c-a7ab-36af9ca04a4d',
                'type': 'message',
                'text': 'this thread message will be edited',
                'user': 'U01GQ7UFKFX',
                'ts': '1633981229.008900',
                'team': 'T01GZF7DHKN',
                'blocks': [
                    {
                        'type': 'rich_text',
                        'block_id': 'CnBA',
                        'elements': [
                            {
                                'type': 'rich_text_section',
                                'elements': [
                                    {
                                        'type': 'text',
                                        'text': 'this thread message will be edited',
                                    }
                                ],
                            }
                        ],
                    }
                ],
                'thread_ts': '1633912633.008700',
                'parent_user_id': 'U01GQ7UFKFX',
            },
            'event_ts': '1633981255.009100',
            'ts': '1633981255.009100',
            'channel_type': 'channel',
        }
        dispatcher.reset_mock()
        listener.message(message)
        dispatcher.message.assert_not_called()
        dispatcher.edit.assert_called_once_with(
            context=SlackContext(
                app=app,
                channel='C01GTHYEU4B',
                channel_type=ChannelType.PUBLIC,
                team='T01GZF7DHKN',
                thread=None,
                timestamp='1633981255.009100',
            ),
            text='this thread message was edited',
            previous_text='this thread message will be edited',
            sender='U01GQ7UFKFX',
            sender_type=SenderType.USER,
            previous_timestamp='1633981229.008900',
            mentions=[],
        )

    @patch('slacker.listeners.SlackListener._channel_info')
    def test_joined_and_left(self, channel_info_mock):
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
        channel_info_mock.reset_mock()
        channel_info_mock.side_effect = [
            {'id': 'C01GTHYEU4B', 'name': '#bot-dev', 'is_channel': True}
        ]
        dispatcher.reset_mock()
        listener.member_joined_channel(member_joined_channel)
        channel_info_mock.assert_called_once_with('C01GTHYEU4B')
        dispatcher.added.assert_called_once_with(
            context=SlackContext(
                app=app,
                channel='C01GTHYEU4B',
                channel_type=ChannelType.PUBLIC,
                team='T01GZF7DHKN',
                timestamp='1633815284.005500',
            ),
            inviter='U01GQ7UFKFX',
        )
        ch = Channel.objects.get(id='C01GTHYEU4B')
        self.assertEquals('#bot-dev', ch.name)
        self.assertEquals(ChannelType.PUBLIC, ch.channel_type_enum)

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
        channel_info_mock.reset_mock()
        dispatcher.reset_mock()
        listener.message(message)
        dispatcher.removed.assert_called_once_with(
            context=SlackContext(
                app=app,
                channel='C01GTHYEU4B',
                channel_type=ChannelType.PUBLIC,
                team='T01GZF7DHKN',
                timestamp='1633814854.000100',
            ),
            remover='U01GQ7UFKFX',
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
        channel_info_mock.reset_mock()
        channel_info_mock.side_effect = [
            {
                'id': 'C01UTGR299A',
                'name': '#bot-dev-private',
                'is_channel': False,
                'is_group': True,
            }
        ]
        dispatcher.reset_mock()
        listener.member_joined_channel(member_joined_channel)
        dispatcher.added.assert_called_once_with(
            context=SlackContext(
                app=app,
                channel='C01UTGR299A',
                channel_type=ChannelType.PRIVATE,
                team='T01GZF7DHKN',
                timestamp='1633816538.000800',
            ),
            inviter='U01GQ7UFKFX',
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
        channel_info_mock.reset_mock()
        dispatcher.reset_mock()
        listener.message(message)
        dispatcher.removed.assert_called_once_with(
            context=SlackContext(
                app=app,
                channel='C01UTGR299A',
                channel_type=ChannelType.PRIVATE,
                team='T01GZF7DHKN',
                timestamp='1633816442.000100',
            ),
            remover='U01GQ7UFKFX',
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
        channel_info_mock.reset_mock()
        dispatcher.reset_mock()
        listener.message(message)
        listener.member_joined_channel(member_joined_channel)
        dispatcher.joined.assert_called_once_with(
            context=SlackContext(
                app=app,
                channel='C01GTHYEU4B',
                channel_type=ChannelType.PUBLIC,
                team='T01GZF7DHKN',
                timestamp='1633815843.006500',
            ),
            joiner='U01GQ7UFKFX',
            # TODO: what about when invited
            inviter=None,
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
        channel_info_mock.reset_mock()
        dispatcher.reset_mock()
        listener.member_left_channel(member_left_channel)
        dispatcher.left.assert_called_once_with(
            context=SlackContext(
                app=app,
                channel='C01GTHYEU4B',
                channel_type=ChannelType.PUBLIC,
                team='T01GZF7DHKN',
                timestamp='1633815668.006400',
            ),
            leaver='U01GQ7UFKFX',
            # TODO: what about when kicked by someone
            kicker=None,
        )
        dispatcher.message.assert_not_called()

    def test_commands(self):
        app = DummyApp()
        dispatcher = MagicMock()
        listener = SlackListener(dispatcher=dispatcher, app=app)

        # message in public channel front-@ mentioning bot
        message = {
            'client_msg_id': '07a49c9c-af26-451d-9f63-36d2e4e77b64',
            'type': 'message',
            'text': '<@U01V6PW6XDE> hi there',
            'user': 'U01GQ7UFKFX',
            'ts': '1633911893.007300',
            'team': 'T01GZF7DHKN',
            'blocks': [
                {
                    'type': 'rich_text',
                    'block_id': 'gah',
                    'elements': [
                        {
                            'type': 'rich_text_section',
                            'elements': [
                                {'type': 'user', 'user_id': 'U01V6PW6XDE'},
                                {'type': 'text', 'text': ' hi there'},
                            ],
                        }
                    ],
                }
            ],
            'channel': 'C01GTHYEU4B',
            'event_ts': '1633911893.007300',
            'channel_type': 'channel',
        }
        listener._auth_info = {'user_id': 'U01V6PW6XDE'}
        dispatcher.reset_mock()
        listener.message(message)
        dispatcher.message.assert_not_called()
        dispatcher.command.assert_called_once_with(
            context=SlackContext(
                app=app,
                channel='C01GTHYEU4B',
                channel_type=ChannelType.PUBLIC,
                team='T01GZF7DHKN',
                thread=None,
                timestamp='1633911893.007300',
            ),
            command='hi',
            text='there',
            sender='U01GQ7UFKFX',
            sender_type=SenderType.USER,
            mentions=[],
        )

        # message in public channel with command leader `.`
        message = {
            'client_msg_id': '07a49c9c-af26-451d-9f63-36d2e4e77b64',
            'type': 'message',
            'text': '.hi there',
            'user': 'U01GQ7UFKFX',
            'ts': '1633911893.007300',
            'team': 'T01GZF7DHKN',
            'blocks': [
                {
                    'type': 'rich_text',
                    'block_id': 'gah',
                    'elements': [
                        {
                            'type': 'rich_text_section',
                            'elements': [{'type': 'text', 'text': '.hi there'}],
                        }
                    ],
                }
            ],
            'channel': 'C01GTHYEU4B',
            'event_ts': '1633911893.007300',
            'channel_type': 'channel',
        }
        dispatcher.reset_mock()
        listener.message(message)
        dispatcher.command.assert_called_once_with(
            context=SlackContext(
                app=app,
                channel='C01GTHYEU4B',
                channel_type=ChannelType.PUBLIC,
                team='T01GZF7DHKN',
                thread=None,
                timestamp='1633911893.007300',
            ),
            command='hi',
            text='there',
            sender='U01GQ7UFKFX',
            sender_type=SenderType.USER,
            mentions=[],
        )
        dispatcher.message.assert_not_called()

        # command in thread
        message = {
            'client_msg_id': '000340b4-210c-443e-ae68-3ce21e3aa68e',
            'type': 'message',
            'text': '<@U01V6PW6XDE>  command in thread',
            'user': 'U01GQ7UFKFX',
            'ts': '1633990282.009400',
            'team': 'T01GZF7DHKN',
            'blocks': [
                {
                    'type': 'rich_text',
                    'block_id': '8o79V',
                    'elements': [
                        {
                            'type': 'rich_text_section',
                            'elements': [
                                {'type': 'user', 'user_id': 'U01V6PW6XDE'},
                                {'type': 'text', 'text': ' command in thread'},
                            ],
                        }
                    ],
                }
            ],
            'thread_ts': '1633912633.008700',
            'parent_user_id': 'U01GQ7UFKFX',
            'channel': 'C01GTHYEU4B',
            'event_ts': '1633990282.009400',
            'channel_type': 'channel',
        }
        dispatcher.reset_mock()
        listener.message(message)
        dispatcher.command.assert_called_once_with(
            context=SlackContext(
                app=app,
                channel='C01GTHYEU4B',
                channel_type=ChannelType.PUBLIC,
                team='T01GZF7DHKN',
                thread='1633912633.008700',
                timestamp='1633990282.009400',
            ),
            command='command',
            text='in thread',
            sender='U01GQ7UFKFX',
            sender_type=SenderType.USER,
            mentions=[],
        )
        dispatcher.message.assert_not_called()

        # message in public change @ mentioning bot in the middle of the
        # message, not a command
        message = {
            'client_msg_id': '878bf483-05f5-45d5-b14a-2814b9920a9d',
            'type': 'message',
            'text': 'hello <@U01V6PW6XDE> and <@U01V6PW6XDF> blah blah',
            'user': 'U01GQ7UFKFX',
            'ts': '1633912018.007600',
            'team': 'T01GZF7DHKN',
            'blocks': [
                {
                    'type': 'rich_text',
                    'block_id': 'mU+tR',
                    'elements': [
                        {
                            'type': 'rich_text_section',
                            'elements': [
                                {'type': 'text', 'text': 'hello '},
                                {'type': 'user', 'user_id': 'U01V6PW6XDE'},
                                {'type': 'text', 'text': ' and '},
                                {'type': 'user', 'user_id': 'U01V6PW6XDF'},
                                {'type': 'text', 'text': ' blah blah'},
                            ],
                        }
                    ],
                }
            ],
            'channel': 'C01GTHYEU4B',
            'event_ts': '1633912018.007600',
            'channel_type': 'channel',
        }
        dispatcher.reset_mock()
        listener.message(message)
        dispatcher.command.assert_not_called()
        dispatcher.message.assert_called_once_with(
            context=SlackContext(
                app=app,
                channel='C01GTHYEU4B',
                channel_type=ChannelType.PUBLIC,
                team='T01GZF7DHKN',
                thread=None,
                timestamp='1633912018.007600',
            ),
            text='hello <@U01V6PW6XDE> and <@U01V6PW6XDF> blah blah',
            sender='U01GQ7UFKFX',
            sender_type=SenderType.USER,
            mentions=['U01V6PW6XDE', 'U01V6PW6XDF'],
        )

        # message in public channel with front-@ mention that doesn't match our
        # bot
        listener._auth_info = {'user_id': 'U01GQ7UFKFX'}
        listener._bot_mention = None
        dispatcher.reset_mock()
        # reusing previous message
        listener.message(message)
        dispatcher.command.assert_not_called()
        dispatcher.message.assert_called_once()

    def test_rich_methods(self):
        app = DummyApp()
        dispatcher = MagicMock()
        listener = SlackListener(dispatcher=dispatcher, app=app)
        listener._auth_info = {'user_id': 'U01GQ7UFKFX'}

        # message with a link to a channel
        message = {
            'client_msg_id': '1c880ba5-6d09-426d-8afe-1e2a847c78cd',
            'type': 'message',
            'text': 'you should check out <#C01JLBRLZ7X|greetings>',
            'user': 'U01GQ7UFKFX',
            'ts': '1633912278.007800',
            'team': 'T01GZF7DHKN',
            'blocks': [
                {
                    'type': 'rich_text',
                    'block_id': 'VlO',
                    'elements': [
                        {
                            'type': 'rich_text_section',
                            'elements': [
                                {
                                    'type': 'text',
                                    'text': 'you should check out ',
                                },
                                {
                                    'type': 'channel',
                                    'channel_id': 'C01JLBRLZ7X',
                                },
                            ],
                        }
                    ],
                }
            ],
            'channel': 'C01GTHYEU4B',
            'event_ts': '1633912278.007800',
            'channel_type': 'channel',
        }
        dispatcher.reset_mock()
        listener.message(message)
        dispatcher.message.assert_called_once_with(
            context=SlackContext(
                app=app,
                channel='C01GTHYEU4B',
                channel_type=ChannelType.PUBLIC,
                team='T01GZF7DHKN',
                thread=None,
                timestamp='1633912278.007800',
            ),
            text='you should check out <#C01JLBRLZ7X|greetings>',
            sender='U01GQ7UFKFX',
            sender_type=SenderType.USER,
            mentions=[],
        )

        # mention other user
        message = {
            'client_msg_id': 'c7f5d060-2b18-41c2-a772-8017eb0d397c',
            'type': 'message',
            'text': 'hello there <@U01JBS2C6E9>',
            'user': 'U01GQ7UFKFX',
            'ts': '1633912414.008200',
            'team': 'T01GZF7DHKN',
            'blocks': [
                {
                    'type': 'rich_text',
                    'block_id': '1Jpc',
                    'elements': [
                        {
                            'type': 'rich_text_section',
                            'elements': [
                                {'type': 'text', 'text': 'hello there '},
                                {'type': 'user', 'user_id': 'U01JBS2C6E9'},
                            ],
                        }
                    ],
                }
            ],
            'channel': 'C01GTHYEU4B',
            'event_ts': '1633912414.008200',
            'channel_type': 'channel',
        }
        dispatcher.reset_mock()
        listener.message(message)
        dispatcher.message.assert_called_once_with(
            context=SlackContext(
                app=app,
                channel='C01GTHYEU4B',
                channel_type=ChannelType.PUBLIC,
                team='T01GZF7DHKN',
                thread=None,
                timestamp='1633912414.008200',
            ),
            text='hello there <@U01JBS2C6E9>',
            sender='U01GQ7UFKFX',
            sender_type=SenderType.USER,
            mentions=['U01JBS2C6E9'],
        )
