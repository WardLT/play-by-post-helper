"""Functions that make Modron interactive

Holds logic of how Modron should respond a certain direct message"""
import shlex
import logging
from argparse import ArgumentParser
from threading import Thread
from time import sleep
from typing import Union, Sequence, Callable

from modron.interact._argparse import NoExitParserError, NoExitParser

from modron.interact.base import SlashCommandPayload, InteractionModule
from modron.interact.dice_roll import DiceRollInteraction
from modron.slack import BotClient
from modron.utils import escape_slack_characters

logger = logging.getLogger(__name__)


_modules = (DiceRollInteraction,)


def _pause_then_run(func: Callable, *args, **kwargs):
    """Pause for a short period and then run a function

    Args:
        func (Callable): Function to run
    """
    sleep(3)
    func(*args, **kwargs)


_description='''A Slack command to handle common D&D computations

At present, it only does dice rolls.

Roll dice by calling `/modron roll`. 
The `roll` command takes the list of dice to roll and any modifiers.
For example, `/modron roll 1d20-1` rolls a d20 with a -1 modifier.
Call `/modron roll --help` for more examples. 
'''


def assemble_parser(client: BotClient, modules: Sequence[InteractionModule.__class__] = _modules) -> NoExitParser:
    """Generate the argument parser and interaction models

    Args:
        client (BotClient): Client to be used by the interaction modules
        modules ([InteractionModule]): List of modules to use for this parser
    Returns:
        (NoExitParser): Parser to use for receiving commands
    """

    # Assemble the root parser
    parser = NoExitParser(description=_description, add_help=True, prog='/modron')

    # Register the modules
    subparsers = parser.add_subparsers(title='available commands',
                                       description='The different ways to interact with Modron.',
                                       dest='subcommand')
    for module in modules:
        module_inst = module(client)
        subparser = subparsers.add_parser(module_inst.name,
                                          description=module_inst.description,
                                          help=module_inst.help_string,
                                          add_help=True)
        module_inst.register_argparse(subparser)
        subparser.set_defaults(interact=module_inst.interact)

    logger.info(f'Created a parse function with {len(modules)} interaction modules')
    return parser


def handle_slash_command(payload: SlashCommandPayload, parser: NoExitParser) -> Union[dict, str]:
    """Respond to a slash command received from Slack

    Args:
        payload (SlashCommandPayload): Slash command data sent from Slack
        parser (ArgumentParser): Parser to use to understand command
    Returns:
        (dict) Immediate reply to give to Slack
    """

    # Parse the command
    try:
        args = parser.parse_args(shlex.split(payload.text))
    except NoExitParserError as exc:
        # Make the reply message
        msg = ''
        if exc.error_message != "":
            msg = f'*{exc.error_message}*\n'
        msg += exc.text_output

        return {
            'text': escape_slack_characters(msg),
            'mkdwn': True
        }

    # If there is not an interact command, return help message
    if not hasattr(args, 'interact'):
        parser.print_help()
        return {
            'text': parser.text_buffer.getvalue(),
            'mkdwn': True
        }

    # Run the specified command in a Thread
    #  Allows this function
    responder = Thread(target=_pause_then_run, args=(args.interact, args, payload))
    responder.start()

    return {"response_type": "in_channel"}
