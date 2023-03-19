import os
import sys
import logging
from logging.handlers import RotatingFileHandler

from discord import Intents

from modron.bot import ModronClient
from modron.interact import attach_commands
from modron.interact.character import HPTracker, CharacterSheet
from modron.interact.dice_roll import DiceRollInteraction
from modron.interact.npc import NPCGenerator
from modron.interact.reminder import ReminderModule, FollowupModule
from modron.interact.stats import StatisticModule


def main(testing: bool = True):
    """Launch the bot"""

    # Write logs only in test mode
    if not testing:
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            handlers=[RotatingFileHandler('modron.log', mode='a',
                                                          maxBytes=1024 * 1024 * 2,
                                                          backupCount=1),
                                      logging.StreamHandler(sys.stdout)])

    # Get the secure tokens
    BOT_TOKEN = os.environ.get('BOT_TOKEN')
    if BOT_TOKEN is None:
        raise ValueError('Bot token not found. Set the BOT_TOKEN environmental variable')
    bot = ModronClient(command_prefix="$", intents=Intents.default())
    bot.testing = testing

    # Generate the slash command responder
    modules = [
        FollowupModule(bot),
        DiceRollInteraction(),
        HPTracker(),
        CharacterSheet(),
        ReminderModule(),
        StatisticModule(),
        NPCGenerator()
    ]
    attach_commands(bot, modules)

    bot.run(BOT_TOKEN)
