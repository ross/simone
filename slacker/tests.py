from datetime import datetime, timezone
from mock import MagicMock, patch
from django.test import TestCase

from simone.context import ChannelType
from .models import Channel, Workspace
from .listeners import SenderType, SlackContext, SlackListener


class DummyApp(object):
    def event(self, *args, **kwargs):
        # Won't be using these so just ignore them
        return lambda _: None


# Bolt injects a BoltContext dict-like object; for tests a plain dict works.
def bolt_context(team_id='T01GZF7DHKN', bot_user_id='U01V6PW6XDE'):
    return {'team_id': team_id, 'bot_user_id': bot_user_id}


def make_workspace(
    team_id='T01GZF7DHKN',
    bot_user_id='U01V6PW6XDE',
    bot_token='xoxb-test',
    bot_id='B01TEST',
):
    return Workspace.objects.get_or_create(
        team_id=team_id,
        defaults={
            'team_name': 'Test Workspace',
            'bot_token': bot_token,
            'bot_id': bot_id,
            'bot_user_id': bot_user_id,
            'installed_at': datetime(2021, 10, 10, tzinfo=timezone.utc),
        },
    )[0]


class TestSlackContext(TestCase):
    def test_channel_types(self):
        ws = make_workspace()
        client = MagicMock()
        public_channel = Channel.objects.create(
            id='C01GTHYEU4B',
            name='bot-dev',
            channel_type=Channel.Type.PUBLIC,
            workspace=ws,
        )
        context = SlackContext(
            client=client,
            channel=public_channel,
            thread=None,
            timestamp='1633815504.005800',
            bot_user_id='U01V6PW6XDE',
        )
        self.assertEqual(ChannelType.PUBLIC, context.channel_type)

        private_channel = Channel.objects.create(
            id='C01UTGR299A',
            name='bot-dev-private',
            channel_type=Channel.Type.PRIVATE,
            workspace=ws,
        )
        context = SlackContext(
            client=client,
            channel=private_channel,
            thread=None,
            timestamp='1633816328.000200',
            bot_user_id='U01V6PW6XDE',
        )
        self.assertEqual(ChannelType.PRIVATE, context.channel_type)


class TestSlackListener(TestCase):
    def setUp(self):
        self.workspace = make_workspace()
        self.client = MagicMock()
        self.bolt_ctx = bolt_context()

    def _ctx(self, channel, thread=None, timestamp=None):
        '''Build a SlackContext the same way the listener does, for assert comparisons.'''
        return SlackContext(
            client=self.client,
            channel=channel,
            thread=thread,
            timestamp=timestamp,
            bot_user_id=self.workspace.bot_user_id,
            workspace=self.workspace,
        )

    def test_messages(self):
        app = DummyApp()
        dispatcher = MagicMock()
        dispatcher.LEADER = '.'
        listener = SlackListener(dispatcher=dispatcher, app=app)

        public_channel = Channel.objects.create(
            id='C01GTHYEU4B',
            name='bot-dev',
            channel_type=Channel.Type.PUBLIC,
            workspace=self.workspace,
        )
        private_channel = Channel.objects.create(
            id='C01UTGR299A',
            name='bot-dev-private',
            channel_type=Channel.Type.PRIVATE,
            workspace=self.workspace,
        )

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
        listener.message(
            message, client=self.client, bolt_context=self.bolt_ctx
        )
        dispatcher.message.assert_called_once_with(
            context=self._ctx(public_channel, timestamp='1633815504.005800'),
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
        listener.message(
            message, client=self.client, bolt_context=self.bolt_ctx
        )
        dispatcher.message.assert_called_once_with(
            context=self._ctx(
                public_channel,
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
        listener.message(
            message, client=self.client, bolt_context=self.bolt_ctx
        )
        dispatcher.message.assert_called_once_with(
            context=self._ctx(public_channel, timestamp='1633888275.007000'),
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
        listener.message(
            message, client=self.client, bolt_context=self.bolt_ctx
        )
        dispatcher.message.assert_called_once_with(
            context=self._ctx(private_channel, timestamp='1633816328.000200'),
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
        listener.message(
            message, client=self.client, bolt_context=self.bolt_ctx
        )
        dispatcher.message.assert_called_once_with(
            context=self._ctx(public_channel, timestamp='1633912633.008700'),
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
        listener.message(
            message, client=self.client, bolt_context=self.bolt_ctx
        )
        dispatcher.message.assert_not_called()
        dispatcher.edit.assert_called_once_with(
            context=self._ctx(public_channel, timestamp='1633912640.008800'),
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
        listener.message(
            message, client=self.client, bolt_context=self.bolt_ctx
        )
        dispatcher.message.assert_called_once_with(
            context=self._ctx(
                public_channel,
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
        listener.message(
            message, client=self.client, bolt_context=self.bolt_ctx
        )
        dispatcher.message.assert_not_called()
        dispatcher.edit.assert_called_once_with(
            context=self._ctx(public_channel, timestamp='1633981255.009100'),
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
        dispatcher.LEADER = '.'
        listener = SlackListener(dispatcher=dispatcher, app=app)

        ephemeral_channel = Channel(
            id='C01GTHYEU4B', name='bot-dev', channel_type=Channel.Type.PUBLIC
        )

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
            {'id': 'C01GTHYEU4B', 'name': 'bot-dev', 'is_channel': True}
        ]
        dispatcher.reset_mock()
        listener.member_joined_channel(
            member_joined_channel,
            client=self.client,
            bolt_context=self.bolt_ctx,
        )
        channel_info_mock.assert_called_once_with(self.client, 'C01GTHYEU4B')
        dispatcher.added.assert_called_once_with(
            context=self._ctx(ephemeral_channel, timestamp='1633815284.005500'),
            inviter='U01GQ7UFKFX',
        )
        public_channel = Channel.objects.get(id='C01GTHYEU4B')
        self.assertEqual('C01GTHYEU4B', public_channel.id)
        self.assertEqual('bot-dev', public_channel.name)
        self.assertEqual(Channel.Type.PUBLIC, public_channel.channel_type)

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
        # the removed message will come from a DM
        channel_info_mock.side_effect = [
            {
                'id': 'D01UDTE3E8M',
                'user': 'USLACKBOT',
                'is_channel': False,
                'is_group': False,
                'is_private': True,
            }
        ]
        dispatcher.reset_mock()
        listener.message(
            message, client=self.client, bolt_context=self.bolt_ctx
        )
        dispatcher.removed.assert_called_once_with(
            context=self._ctx(public_channel, timestamp='1633814854.000100'),
            remover='U01GQ7UFKFX',
        )

        private_channel = Channel.objects.create(
            id='C01UTGR299A',
            name='bot-dev-private',
            channel_type=Channel.Type.PRIVATE,
            workspace=self.workspace,
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
                'name': 'bot-dev-private',
                'is_channel': False,
                'is_group': True,
            }
        ]
        dispatcher.reset_mock()
        listener.member_joined_channel(
            member_joined_channel,
            client=self.client,
            bolt_context=self.bolt_ctx,
        )
        dispatcher.added.assert_called_once_with(
            context=self._ctx(private_channel, timestamp='1633816538.000800'),
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
        listener.message(
            message, client=self.client, bolt_context=self.bolt_ctx
        )
        dispatcher.removed.assert_called_once_with(
            context=self._ctx(private_channel, timestamp='1633816442.000100'),
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
        listener.message(
            message, client=self.client, bolt_context=self.bolt_ctx
        )
        listener.member_joined_channel(
            member_joined_channel,
            client=self.client,
            bolt_context=self.bolt_ctx,
        )
        dispatcher.joined.assert_called_once_with(
            context=self._ctx(public_channel, timestamp='1633815843.006500'),
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
        listener.member_left_channel(
            member_left_channel, client=self.client, bolt_context=self.bolt_ctx
        )
        dispatcher.left.assert_called_once_with(
            context=self._ctx(public_channel, timestamp='1633815668.006400'),
            leaver='U01GQ7UFKFX',
            # TODO: what about when kicked by someone
            kicker=None,
        )
        dispatcher.message.assert_not_called()

    def test_commands(self):
        app = DummyApp()
        dispatcher = MagicMock()
        dispatcher.LEADER = '.'
        listener = SlackListener(dispatcher=dispatcher, app=app)

        public_channel = Channel.objects.create(
            id='C01GTHYEU4B',
            name='bot-dev',
            channel_type=Channel.Type.PUBLIC,
            workspace=self.workspace,
        )

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
        dispatcher.reset_mock()
        listener.message(
            message, client=self.client, bolt_context=self.bolt_ctx
        )
        dispatcher.message.assert_not_called()
        dispatcher.command.assert_called_once_with(
            context=self._ctx(public_channel, timestamp='1633911893.007300'),
            text='hi there',
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
        listener.message(
            message, client=self.client, bolt_context=self.bolt_ctx
        )
        dispatcher.command.assert_called_once_with(
            context=self._ctx(public_channel, timestamp='1633911893.007300'),
            text='hi there',
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
        listener.message(
            message, client=self.client, bolt_context=self.bolt_ctx
        )
        dispatcher.command.assert_called_once_with(
            context=self._ctx(
                public_channel,
                thread='1633912633.008700',
                timestamp='1633990282.009400',
            ),
            text=' command in thread',
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
        listener.message(
            message, client=self.client, bolt_context=self.bolt_ctx
        )
        dispatcher.command.assert_not_called()
        dispatcher.message.assert_called_once_with(
            context=self._ctx(public_channel, timestamp='1633912018.007600'),
            text='hello <@U01V6PW6XDE> and <@U01V6PW6XDF> blah blah',
            sender='U01GQ7UFKFX',
            sender_type=SenderType.USER,
            mentions=['U01V6PW6XDE', 'U01V6PW6XDF'],
        )

        # message in public channel with front-@ mention that doesn't match our
        # bot — simulate by using a different bot_user_id in bolt_context
        other_bolt_ctx = bolt_context(
            team_id='T01GZF7DHKN', bot_user_id='U01GQ7UFKFX'
        )
        dispatcher.reset_mock()
        # reusing previous message
        listener.message(
            message, client=self.client, bolt_context=other_bolt_ctx
        )
        dispatcher.command.assert_not_called()
        dispatcher.message.assert_called_once()

    def test_rich_methods(self):
        app = DummyApp()
        dispatcher = MagicMock()
        dispatcher.LEADER = '.'
        listener = SlackListener(dispatcher=dispatcher, app=app)

        public_channel = Channel.objects.create(
            id='C01GTHYEU4B',
            name='bot-dev',
            channel_type=Channel.Type.PUBLIC,
            workspace=self.workspace,
        )

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
        listener.message(
            message, client=self.client, bolt_context=self.bolt_ctx
        )
        dispatcher.message.assert_called_once_with(
            context=self._ctx(public_channel, timestamp='1633912278.007800'),
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
        listener.message(
            message, client=self.client, bolt_context=self.bolt_ctx
        )
        dispatcher.message.assert_called_once_with(
            context=self._ctx(public_channel, timestamp='1633912414.008200'),
            text='hello there <@U01JBS2C6E9>',
            sender='U01GQ7UFKFX',
            sender_type=SenderType.USER,
            mentions=['U01JBS2C6E9'],
        )

    def test_channel_rename(self):
        app = DummyApp()
        listener = SlackListener(dispatcher=None, app=app)
        dummy_client = MagicMock()
        dummy_bolt_ctx = bolt_context()

        # create a channel we've never seen before
        event = {
            'type': 'channel_rename',
            'channel': {
                'id': 'C02JNLHRQ3W',
                'is_channel': True,
                'is_mpim': False,
                'name': 'bot-dev-rename-2',
                'name_normalized': 'bot-dev-rename-2',
                'created': 1634828436,
            },
            'event_ts': '1634828547.000900',
        }
        listener.channel_rename(
            event, client=dummy_client, bolt_context=dummy_bolt_ctx
        )
        # check that it now exists
        channel = Channel.objects.get(id='C02JNLHRQ3W')
        # and has the expected name
        self.assertEqual('bot-dev-rename-2', channel.name)

        # Another rename of the same channel
        event = {
            'type': 'channel_rename',
            'channel': {
                'id': 'C02JNLHRQ3W',
                'is_channel': True,
                'is_mpim': False,
                'name': 'bot-dev-rename',
                'name_normalized': 'bot-dev-rename',
                'created': 1634828436,
            },
            'event_ts': '1634828547.000900',
        }
        listener.channel_rename(
            event, client=dummy_client, bolt_context=dummy_bolt_ctx
        )
        # reload our object and see if the name changed
        channel.refresh_from_db()
        self.assertEqual('bot-dev-rename', channel.name)
