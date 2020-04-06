"""Tests the functions used to interface with interaction modules"""
import logging
import os

from pytest import fixture, raises

from modron.interact import assemble_parser, NoExitParser, NoExitParserError, SlashCommandPayload
from modron.slack import BotClient


@fixture
def payload(client) -> SlashCommandPayload:
    return SlashCommandPayload(
        command='/modron',
        text='{... define in test if you need ...}',
        response_url='https://httpstat.us/200',
        trigger_id='yes',
        user_id=client.my_id,
        channel_id=client.get_channel_id('bot_test')
    )


@fixture()
def client() -> BotClient:
    token = os.environ.get('OAUTH_ACCESS_TOKEN', None)
    if token is None:
        raise ValueError('Cannot find Auth token')
    return BotClient(token=token)


@fixture()
def parser(client) -> NoExitParser:
    return assemble_parser(client)


def test_help(parser):
    """We expect help commands to raise an error that contains both the error message and any printed messages"""
    parser.parse_args(['--help'])
    assert parser.text_buffer.getvalue().startswith('usage: /modron')


def test_roll_help(parser):
    with raises(NoExitParserError) as exc:
        parser.parse_args(['roll', '--help'])
    assert exc.value.text_output.startswith('usage: /modron roll')
    assert exc.value.error_message.startswith('the following arguments')


def test_rolling(parser, payload, caplog):
    # Parse args and run the event
    args = parser.parse_args(['roll', '1d6+1'])
    with caplog.at_level(logging.INFO):
        args.interact(args, payload)

    assert '1d6+1' in caplog.messages[0]
