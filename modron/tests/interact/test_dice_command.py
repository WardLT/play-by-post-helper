from argparse import ArgumentParser
from datetime import datetime
from csv import DictReader
from time import sleep
import os

from discord import Guild, utils, TextChannel
from pytest import raises, fixture, mark

from modron.discord import timestamp_to_local_tz
from modron.interact._argparse import NoExitParserError
from modron.config import config
from modron.interact.dice_roll import DiceRollInteraction
from modron.tests.interact.conftest import MockContext


@fixture()
def roller(guild) -> DiceRollInteraction:
    config.team_options[guild.id].blind_channel = 'bot_testing'
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

    # Test a luck roll (always a d20)
    args = parser.parse_args(['--show', 'luck'])
    await roller.interact(args, payload)
    assert 'for luck' in payload.last_message

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
        for roll in reader:
            continue  # Loop until the last one
        assert roll['reason'] == 'test'
        assert roll['advantage']
        assert roll['channel'] == 'ic_all'


@mark.asyncio
async def test_ability_roll(parser, roller, payload):
    # Test an unknown ability
    args = parser.parse_args(['ability', 'check'])
    with raises(BaseException) as exc:
        await roller.interact(args, payload)
    assert str(exc.value).startswith('Unrecognized')

    # Test a real ability
    args = parser.parse_args(['-a', 'str', 'save'])
    await roller.interact(args, payload)
    assert 'at advantage' in payload.last_message

    # Test an alias
    args = parser.parse_args(['cheat'])
    await roller.interact(args, payload)
    assert '20' in payload.last_message


@mark.asyncio()
async def test_blind_roll(parser, roller, payload, guild: Guild):
    # Make perception rolls blind
    config.team_options[guild.id].blind_rolls = ['perception']

    # Test a blind roll
    args = parser.parse_args(['luck', '--blind'])
    assert args.blind is not None
    assert args.blind
    await roller.interact(args, payload)
    assert 'only the GM will see the result' in payload.last_message

    # See if it was reported in the "blind_channel"
    sleep(5)
    reminder_channel: TextChannel = utils.get(guild.channels, name="bot_testing")
    async for last_message in reminder_channel.history(limit=1, oldest_first=False):
        break
    assert (timestamp_to_local_tz(last_message.created_at) - datetime.now()).total_seconds() < 5
    await last_message.delete()

    # Make sure perception starts out at blind
    args = parser.parse_args(['perception'])
    await roller.interact(args, payload)
    assert 'only the GM will see the result' in payload.last_message
    sleep(5)
    await reminder_channel.last_message.delete()

    # Make sure blindness can be overridden
    args = parser.parse_args(['perception', '--show'])
    await roller.interact(args, payload)
    assert 'only the GM will see the result' not in payload.last_message


@mark.asyncio()
async def test_public_channel(parser, roller, payload, guild: Guild):
    """Test routing rolls to a public channel"""
    # Set the public channel
    config.team_options[guild.id].public_channel = 'bot_testing'
    config.team_options[guild.id].watch_channels.append('bot_testing')

    # Test a regular roll
    args = parser.parse_args(['luck', '--show'])
    await roller.interact(args, payload)
    assert payload.last_message is None  # No roll in that channel
    channel: TextChannel = utils.get(guild.channels, name='bot_testing')
    msg = channel.last_message
    assert 'luck' in msg.clean_content
    await msg.delete()

    # Test a blind roll
    args = parser.parse_args(['luck', '--blind'])
    assert args.blind is not None
    assert args.blind
    await roller.interact(args, payload)
    assert 'only the GM will see the result' in payload.last_message

    # Make sure it replies back on a private channel
    payload.channel.name = 'bot_testing_gm'
    config.team_options[guild.id].watch_channels.append('bot_testing_gm')
    args = parser.parse_args(['luck', '--show'])
    await roller.interact(args, payload)
    assert 'luck' in payload.last_message


@mark.asyncio
async def test_set_character(parser, roller, payload):
    payload.channel.name = 'bot_testing_gm'  # Forces it to print to screen

    # Test with a different character
    args = parser.parse_args(['athletics'])
    await roller.interact(args, payload)
    assert "+0" in payload.last_message  # Modron has a +0 str mod

    args = parser.parse_args(['-c', 'adrianna', 'athletics'])
    await roller.interact(args, payload)
    assert "+0" not in payload.last_message  # Adrianna has a good one
