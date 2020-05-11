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
from modron.interact.npc import NPCGenerator
from modron.interact.reminder import ReminderModule
from modron.slack import BotClient
from modron.utils import escape_slack_characters

logger = logging.getLogger(__name__)


_modules = (DiceRollInteraction, NPCGenerator, ReminderModule)


def _pause_then_run(func: Callable, *args, **kwargs):
    """Pause for a short period and then run a function

    Args:
        func (Callable): Function to run
    """
    sleep(0.1)
    func(*args, **kwargs)


_description = '''A Slack command to handle common D&D tasks'''


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

    # Expand shortcut commands
    logger.info(f'Received command: {payload.command} {payload.text}')
    if payload.command != "/modron":
        if not payload.command.startswith('/m'):
            return {
                'text': 'ERROR: your command is not supported by Modron yet :('
            }

        # Determine the sub command name
        subcommand = payload.command[2:]
        payload.text = f'{subcommand} {payload.text}'
        logger.info(f'Expanded shortcut command to the longer-form "/modron {payload.text}')

    # Parse the command
    try:
        args = parser.parse_args(shlex.split(payload.text))
    except NoExitParserError as exc:
        logger.info(f'Parser raised an exception. Message: {exc.error_message}')

        # Make the reply message
        msg = ''
        if exc.error_message is not None:
            msg = f'*{exc.error_message}*\n'
        msg += exc.text_output
        logger.info(f'Sending some help messages back. {repr(msg[:64])}...{len(msg)} char')

        return {
            'text': escape_slack_characters(msg),
            'mrkdwn': True
        }

    # If there is not an interact command, return help message
    if not hasattr(args, 'interact'):
        parser.print_help()
        msg = parser.text_buffer.getvalue()
        logger.info(f'Sending some help messages back. {repr(msg[:64])}...{len(msg)} char')
        return {
            'text': msg,
            'mrkdwn': True
        }

    # Run the specified command in a Thread
    #  Allows this function
    responder = Thread(target=_pause_then_run, args=(args.interact, args, payload))
    responder.start()

    return {"response_type": "in_channel"}
