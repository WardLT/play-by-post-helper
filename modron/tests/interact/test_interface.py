"""Tests the functions used to interface with interaction modules"""
import logging
from time import sleep

from pytest import raises

from modron.interact import NoExitParserError, handle_generic_slash_command
from modron.config import get_config


config = get_config()


def test_help(parser):
    """We expect help commands to raise an error that contains
    both the error message and any printed messages"""
    with raises(NoExitParserError) as exc:
        parser.parse_args(['--help'])
    print(exc.value.text_output)
    assert exc.value.text_output.startswith('*usage*: /modron')


def test_help_payload(payload, parser):
    # Option 1: Using --help
    payload.text = '--help'
    result = handle_generic_slash_command(payload, parser)
    assert len(result['text']) > 10

    # Option 2: Sending nothing
    payload.text = ''
    result = handle_generic_slash_command(payload, parser)
    assert len(result['text']) > 10


def test_handle(parser, payload, caplog):
    payload.text = 'roll 1d20 test'
    with caplog.at_level(logging.INFO):
        assert handle_generic_slash_command(payload, parser) == {"response_type": "in_channel"}
        sleep(5)  # Waits for the delayed thread to run
    assert '1d20' in caplog.messages[-2]


def test_payload_error(parser, payload):
    payload.text = 'roll'
    result = handle_generic_slash_command(payload, parser)
    assert isinstance(result, dict)
