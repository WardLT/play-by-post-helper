"""Tests the functions used to interface with interaction modules"""
import json
import logging
import os
from csv import DictReader
from time import sleep

from pytest import fixture, raises

from modron.interact import assemble_parser, NoExitParser, NoExitParserError, SlashCommandPayload, handle_slash_command
from modron.interact.npc import generate_and_render_npcs
from modron.slack import BotClient
from modron import config


@fixture
def tmp_config(tmpdir):
    config.DICE_LOG = os.path.join(tmpdir, 'dice_log.csv')
    return config


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
    """We expect help commands to raise an error that contains
    both the error message and any printed messages"""
    with raises(NoExitParserError) as exc:
        parser.parse_args(['--help'])
    print(exc.value.text_output)
    assert exc.value.text_output.startswith('*usage*: /modron')


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
        sleep(5)  # Waits for the delayed thread to run
    assert '1d20' in caplog.messages[-2]


def test_shortcut(parser, payload, caplog):
    payload.command = '/mroll'
    payload.text = '1d20 test'
    with caplog.at_level(logging.INFO):
        assert handle_slash_command(payload, parser) == {"response_type": "in_channel"}
        sleep(5)  # Waits for the delayed thread to run
    assert '1d20' in caplog.messages[-2]

    # Special shortcut for /roll
    payload.command = '/roll'
    with caplog.at_level(logging.INFO):
        assert handle_slash_command(payload, parser) == {"response_type": "in_channel"}
        sleep(5)  # Waits for the delayed thread to run
    assert '1d20' in caplog.messages[-2]


def test_roll_help(parser):
    with raises(NoExitParserError) as exc:
        parser.parse_args(['roll', '--help'])
    print(exc.value.text_output)
    assert exc.value.text_output.startswith('*usage*: /modron roll')


def test_rolling(client, parser, payload, caplog, tmp_config):
    # Parse args and run the event
    args = parser.parse_args(['roll', '1d6+1'])
    with caplog.at_level(logging.INFO):
        args.interact(args, payload)
    assert '1d6+1' in caplog.messages[-2]

    # Try rolling with a purpose
    args = parser.parse_args(['roll', '1d6+1', 'test', 'roll'])
    with caplog.at_level(logging.INFO):
        args.interact(args, payload)
    assert '1d6+1 for test roll.' in caplog.messages[-2]

    # Try rolling at advantage
    args = parser.parse_args(['roll', '1d6+1', 'test', '-a'])
    with caplog.at_level(logging.INFO):
        args.interact(args, payload)
    assert '1d6+1 at advantage for test.' in caplog.messages[-2]

    # Make sure the log file does not yet exist
    print(f'Checking for existence of {config.DICE_LOG}')
    assert not os.path.isfile(config.DICE_LOG)
    assert 'skipped channel - True' in caplog.messages[-1]

    # Run a test with ic_all to see if it saves the log
    payload.channel_id = client.get_channel_id('ic_all')
    args = parser.parse_args(['roll', '1d6+1', 'test', '-a'])
    args.interact(args, payload)
    with open(config.DICE_LOG) as fp:
        reader = DictReader(fp)
        roll = next(reader)
        assert roll['reason'] == 'test'
        assert roll['advantage']
        assert roll['channel'] == 'ic_all'


def test_payload_error(parser, payload):
    payload.text = 'roll'
    result = handle_slash_command(payload, parser)
    assert isinstance(result, dict)


def test_npc_generator(parser, payload, caplog):
    try:
        args = parser.parse_args(['npcgen', '3'])
        with caplog.at_level(logging.INFO):
            args.interact(args, payload)
    except OSError as exc:
        assert 'wkhtmltopdf' in str(exc), "Failure for a reason other than wkhtml not being installed"
    assert '3 NPCs from default' in caplog.messages[-1]

    # Print out an example to see how it looks
    example = generate_and_render_npcs('default', 2)
    print(json.dumps(example, indent=2))

    # Test the request coming from a DM
    payload.user_id = 'UP4K437HT'  # Logan Ward's user ID
    payload.channel_id = 'GNOTREALCHID'
    try:
        args = parser.parse_args(['npcgen', '3'])
        with caplog.at_level(logging.INFO):
            args.interact(args, payload)
    except OSError as exc:
        assert 'wkhtmltopdf' in str(exc), "Failure for a reason other than wkhtml not being installed"
    assert '3 NPCs from default' in caplog.messages[-2]
    assert 'Command came from' in caplog.messages[-1]


def test_delay_status(parser, payload):
    args = parser.parse_args(['reminder', 'status'])
    args.interact(args, payload)


def test_delay_pause(parser, payload, caplog):
    args = parser.parse_args(['reminder', 'break', 'PT1S'])
    with caplog.at_level(logging.INFO):
        args.interact(args, payload)
    assert 'failed' not in caplog.messages[-1]
