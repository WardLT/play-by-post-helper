"""Tests the functions used to interface with interaction modules"""
import logging
import os

from pytest import fixture, raises

from modron.interact import assemble_parser, NoExitParser, NoExitParserError, SlashCommandPayload, handle_slash_command
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
    with raises(NoExitParserError) as exc:
        parser.parse_args(['--help'])
    assert exc.value.text_output.startswith('usage: /modron')


def test_help_payload(payload, parser):
    # Option 1: Using --help
    payload.text = '--help'
    result = handle_slash_command(payload, parser)
    assert len(result['text']) > 10

    # Option 2: Sending nothing
    payload.text = ''
    result = handle_slash_command(payload, parser)
    assert len(result['text']) > 10


def test_handle(parser, payload, caplog):
    payload.text = 'roll 1d20 test'
    with caplog.at_level(logging.INFO):
        assert handle_slash_command(payload, parser) == {"response_type": "in_channel"}
    assert '1d20' in caplog.messages[0]


def test_roll_help(parser):
    with raises(NoExitParserError) as exc:
        parser.parse_args(['roll', '--help'])
    assert exc.value.text_output.startswith('usage: /modron roll')


def test_rolling(parser, payload, caplog):
    # Parse args and run the event
    args = parser.parse_args(['roll', '1d6+1'])
    with caplog.at_level(logging.INFO):
        args.interact(args, payload)

    assert '1d6+1' in caplog.messages[0]


def test_payload_error(parser, payload):
    payload.text = 'roll'
    result = handle_slash_command(payload, parser)
    assert isinstance(result, dict)
