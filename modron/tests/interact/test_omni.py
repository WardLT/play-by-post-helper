"""Test the generic $modron command"""
from datetime import datetime
from time import sleep

from pytest import mark
from discord import utils, TextChannel

from modron.bot import ModronClient
from modron.discord import timestamp_to_local_tz
from modron.interact import attach_commands, handle_generic_command
from modron.interact.dice_roll import DiceRollInteraction
from modron.tests.interact.conftest import MockContext


@mark.asyncio()
async def test_omni(bot: ModronClient, payload: MockContext, guild):
    # Make the super-parser
    modules = [DiceRollInteraction()]
    parser = attach_commands(bot, modules)

    # Run the help command
    await handle_generic_command(parser, payload, '-h')
    assert "- `roll`" in payload.last_message

    # Run the roll command
    await handle_generic_command(parser, payload, 'roll', 'd20')
    roll_channel: TextChannel = utils.get(guild.channels, name="bot_testing")
    sleep(5.)
    async for last_message in roll_channel.history(limit=1, oldest_first=False):
        break
    assert (timestamp_to_local_tz(last_message.created_at) - datetime.now()).total_seconds() < 5
    await last_message.delete()

    # Make an error
    await handle_generic_command(parser, payload, 'nope')
    assert "invalid" in payload.last_message
