"""Test the generic $modron command"""

from pytest import mark

from modron.bot import ModronClient
from modron.interact import attach_commands, handle_generic_command
from modron.interact.dice_roll import DiceRollInteraction
from modron.tests.interact.conftest import MockContext


@mark.asyncio()
async def test_omni(bot: ModronClient, payload: MockContext):
    # Make the super-parser
    modules = [DiceRollInteraction()]
    parser = attach_commands(bot, modules)

    # Run the help command
    await handle_generic_command(parser, payload, '-h')
    assert "- `roll`" in payload.last_message

    # Run the roll command
    await handle_generic_command(parser, payload, 'roll', 'd20')
    assert "rolled 1d20" in payload.last_message

    # Make an error
    await handle_generic_command(parser, payload, 'nope')
    print(payload.last_message)
    assert "invalid" in payload.last_message
