#
#
#

from mock import MagicMock
from unittest import TestCase

from simone.message import Event
from simone.slack.message import SlackAddedEvent, SlackJoinedEvent, \
    SlackMessageEvent


class TestSlackMessage(TestCase):
    mock_adapter = MagicMock()

    def test_slack_message_event(self):
        # main channel
        sme = SlackMessageEvent(adapter=self.mock_adapter, sender='u44',
                                text='Hello World!', channel='c42', 
                                channel_type=Event.CHANNEL_PUBLIC)
        self.assertEquals({
            'channel': '<#c42>',
            'sender': '<@u44>',
        }, sme.text_context())

        self.mock_adapter.reset_mock()
        self.assertTrue(sme.reply('Thanks {sender}, sounds good!'))
        self.mock_adapter.say.assert_called_once()
        self.assertEqual({
            'text': 'Thanks <@u44>, sounds good!',
            'channel': 'c42',
            'thread_ts': None,
        }, self.mock_adapter.say.call_args[1])

        # in thread
        sme = SlackMessageEvent(adapter=self.mock_adapter, sender='u44',
                                text='Hello World!', channel='c42', 
                                channel_type=Event.CHANNEL_PUBLIC,
                                thread='t43')

        self.mock_adapter.reset_mock()
        self.assertTrue(sme.reply('Does not compute'))
        self.mock_adapter.say.assert_called_once()
        self.assertEqual({
            'text': 'Does not compute',
            'channel': 'c42',
            'thread_ts': 't43',
        }, self.mock_adapter.say.call_args[1])

    def test_slack_joined_event(self):
        sje = SlackJoinedEvent(adapter=self.mock_adapter, sender='u44',
                               text='Hello World!', channel='c42', 
                               channel_type=Event.CHANNEL_PUBLIC,
                               joiner='u99')
        self.assertEquals({
            'channel': '<#c42>',
            'sender': '<@u44>',
            'joiner': '<@u99>',
        }, sje.text_context())

    def test_slack_added_event(self):
        sje = SlackAddedEvent(adapter=self.mock_adapter, sender='u44',
                              text='Hello World!', channel='c42', 
                              channel_type=Event.CHANNEL_PUBLIC)
        self.assertEquals({
            'channel': '<#c42>',
            'sender': '<@u44>',
        }, sje.text_context())
