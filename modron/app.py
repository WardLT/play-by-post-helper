import os
import sys
import logging
from logging.handlers import RotatingFileHandler

from modron.bot import ModronClient
from modron.interact import attach_commands
from modron.interact.dice_roll import DiceRollInteraction


def main():
    """Launch the bot"""

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
    bot = ModronClient(command_prefix="/")

    # Generate the slash command responder
    modules = [
         DiceRollInteraction(),
    ]
    attach_commands(bot, modules)

    bot.run(BOT_TOKEN)
