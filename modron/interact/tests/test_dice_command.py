from time import sleep
import logging
import os
from csv import DictReader

from pytest import raises

from modron.interact import handle_generic_slash_command
from modron.interact._argparse import NoExitParserError
from modron.config import get_config

config = get_config()


def test_roll_help(parser):
    with raises(NoExitParserError) as exc:
        parser.parse_args(['roll', '--help'])
    print(exc.value.text_output)
    assert exc.value.text_output.startswith('*usage*: /modron roll')


def test_rolling(clients, parser, payload, caplog):
    # Delete any existing log file
    log_path = config.get_dice_log_path(payload.team_id)
    if os.path.isfile(log_path):
        original_time = os.path.getmtime(log_path)
    else:
        original_time = -1

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
    print(f'Checking if the log was created or modified at {log_path}')
    assert not os.path.isfile(log_path) or os.path.getmtime(log_path) == original_time
    assert 'skipped channel - True' in caplog.messages[-1]

    # Run a test with a "direct message" channel
    payload.channel_id = 'GNOTAREALCHANNEL'
    args = parser.parse_args(['roll', '1d6+1', 'test', '-a'])
    with caplog.at_level(logging.INFO):
        args.interact(args, payload)
    assert not os.path.isfile(log_path) or os.path.getmtime(log_path) == original_time
    assert 'private channel - True' in caplog.messages[-1]

    # Run a test with ic_all to see if it saves the log
    payload.channel_id = clients[payload.team_id].get_channel_id('ic_all')
    args = parser.parse_args(['roll', '1d6+1', 'test', '-a'])
    args.interact(args, payload)
    with open(log_path) as fp:
        reader = DictReader(fp)
        roll = next(reader)
        assert roll['reason'] == 'test'
        assert roll['advantage']
        assert roll['channel'] == 'ic_all'


def test_ability_roll(parser, payload, caplog):
    # Test a roll w/o a registered character
    args = parser.parse_args(['roll', 'ability', 'check'])
    with caplog.at_level(logging.INFO):
        args.interact(args, payload)
    assert "needs to register" in caplog.messages[-1]

    # Test an unknown ability
    payload.user_id = 'UP4K437HT'
    args = parser.parse_args(['roll', 'ability', 'check'])
    with raises(ValueError) as exc:
        args.interact(args, payload)
    assert str(exc.value).startswith('Unrecognized')

    # Test a real ability
    args = parser.parse_args(['roll', '-a', 'str', 'save'])
    with caplog.at_level(logging.INFO):
        args.interact(args, payload)
    assert '1d20+7 at advantage for str save.' in caplog.messages[-2]


def test_shortcut(parser, payload, caplog):
    payload.command = '/mroll'
    payload.text = '1d20 test'
    with caplog.at_level(logging.INFO):
        assert handle_generic_slash_command(payload, parser) == {"response_type": "in_channel"}
        sleep(5)  # Waits for the delayed thread to run
    assert '1d20' in caplog.messages[-2]

    # Special shortcut for /roll
    payload.command = '/roll'
    payload.text = '1d20 test'
    with caplog.at_level(logging.INFO):
        assert handle_generic_slash_command(payload, parser) == {"response_type": "in_channel"}
        sleep(5)  # Waits for the delayed thread to run
    assert '1d20' in caplog.messages[-2]
