from argparse import ArgumentParser
import logging
import os
from csv import DictReader

from discord import Guild, utils
from pytest import raises, fixture, mark
from pytest_mock import MockerFixture

from modron.interact._argparse import NoExitParserError
from modron.config import get_config
from modron.interact.dice_roll import DiceRollInteraction
from modron.tests.interact.conftest import MockContext

config = get_config()


@fixture()
def roller() -> DiceRollInteraction:
    return DiceRollInteraction()


@fixture()
def parser(roller) -> ArgumentParser:
    return roller.parser


def test_roll_help(parser):
    with raises(NoExitParserError) as exc:
        parser.parse_args(['roll', '--help'])
    print(exc.value.text_output)
    assert exc.value.text_output.startswith('*usage*: /roll')


@mark.asyncio
async def test_rolling(parser, roller: DiceRollInteraction, payload: MockContext, guild: Guild):
    # Delete any existing log file
    log_path = config.get_dice_log_path(payload.guild.id)
    if os.path.isfile(log_path):
        original_time = os.path.getmtime(log_path)
    else:
        original_time = -1

    # Parse args and run the event
    args = parser.parse_args(['1d6+1'])
    await roller.interact(args, payload)
    assert '1d6+1' in payload.last_message

    # Try rolling with a purpose
    args = parser.parse_args(['1d6+1', 'test', 'roll'])
    await roller.interact(args, payload)
    assert 'rolled for test roll' in payload.last_message
    assert '1d6+1' in payload.last_message

    # Try rolling at advantage
    args = parser.parse_args(['1d6+1', 'test', '-a'])
    await roller.interact(args, payload)
    assert '1d6+1 at advantage' in payload.last_message

    # Make sure the log file does not yet exist
    print(f'Checking if the log was created or modified at {log_path}')
    assert not os.path.isfile(log_path) or os.path.getmtime(log_path) == original_time

    # Run a test with ic_all to see if it saves the log
    payload.channel = utils.get(guild.channels, name='ic_all')
    args = parser.parse_args(['1d6+2', 'test', '-a'])
    await roller.interact(args, payload)
    assert '1d6+2' in payload.last_message
    with open(log_path) as fp:
        reader = DictReader(fp)
        roll = next(reader)
        assert roll['reason'] == 'test'
        assert roll['advantage']
        assert roll['channel'] == 'ic_all'


@mark.asyncio
@mark.skip('Cannot figure out how to mock user')
async def test_ability_roll(parser, roller, payload, mocker: MockerFixture):
    # Test a roll w/o a registered character
    args = parser.parse_args(['ability', 'check'])
    await roller.interact(args, payload)
    assert "you have not registered a character" in payload.last_message

    # Test an unknown ability
    mocker.patch.object(payload.author.id, 'id', new=854826609101111317)
    args = parser.parse_args(['ability', 'check'])
    with raises(BaseException) as exc:
        await roller.interact(args, payload)
    assert str(exc.value).startswith('Unrecognized')

    # Test a real ability
    args = parser.parse_args(['roll', '-a', 'str', 'save'])
    with caplog.at_level(logging.INFO):
        args.roller(args, payload)
    assert '1d20+7 at advantage for str save.' in caplog.messages[-2]
