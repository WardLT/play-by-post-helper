from multiprocessing import Process
from time import sleep

from pytest import mark

from modron.app import main
from modron.bot import ModronClient
from modron.interact.dice_roll import DiceRollInteraction
from modron.interact import attach_commands
from modron.interact.npc import NPCGenerator


def test_launch():
    # Launch Modron as a subprocess
    proc = Process(target=main, daemon=True, kwargs={"testing": True})
    proc.start()

    # Issue a kill command after 30 seconds
    sleep(30)
    proc.terminate()

    # See if it exits cleanly
    proc.join(timeout=30)
    assert proc.exitcode is not None, "Still has not terminated"
    assert proc.exitcode in [0, -15], f"Something went awry. Exitcode: {proc.exitcode}"


@mark.asyncio
def test_register_functions(bot: ModronClient):
    """Ensure that function registration works as advertised"""
    modules = [DiceRollInteraction(), NPCGenerator()]
    attach_commands(bot, modules)

    assert len(bot.commands) == 4  # ['roll', 'modron', 'help', 'npcgen']
    assert bot.all_commands["modron"].signature == "[args...]"

    for module in modules:
        command = bot.all_commands[module.name]
        assert command.signature == "[args...]"
        assert isinstance(command.callback.module, module.__class__)
