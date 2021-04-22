#!/usr/bin/env python

from logging import DEBUG as LOGGING_DEBUG, INFO as LOGGING_INFO, \
    basicConfig, getLogger
from os import environ
from tornado.options import define, options, parse_command_line

from simone import Simone
from simone.slack.adapter import SlackAdapter
from simone import command
from simone import interaction

define('debug', default=False, help='Enable debug mode')
define('address', default='0.0.0.0',
       help='Set the interface to listen on')
define('port', default=9801, help='Port to listen on')

parse_command_line()

basicConfig(level=LOGGING_DEBUG)
getLogger().level=LOGGING_DEBUG

slack_adapter = SlackAdapter(environ.get('STONKS_ITS_BREAK_TIME_OAUTH_TOKEN'),
                             environ.get('STONKS_SIGNING_SECRET'))
simone = Simone(commands=(
    command.Stonks(),
), interactions=(
    interaction.AddedToChannel(),
    interaction.Time(),
), adapter=slack_adapter)

slack_adapter.run(address=options.address, port=options.port,
                  debug=options.debug)
