"""Functions that make Modron interactive

Holds logic of how Modron should respond a certain direct message"""
import shlex
import logging
from threading import Thread
from time import sleep
from typing import Union, Sequence, Callable

from modron.interact._argparse import NoExitParserError, NoExitParser

from modron.interact.base import SlashCommandPayload, InteractionModule
from modron.interact.dice_roll import DiceRollInteraction
from modron.interact.npc import NPCGenerator
from modron.interact.reminder import ReminderModule
from modron.utils import escape_slack_characters

logger = logging.getLogger(__name__)


all_modules = (DiceRollInteraction, NPCGenerator, ReminderModule)


def _pause_then_run(func: Callable, *args, **kwargs):
    """Pause for a short period and then run a function

    Args:
        func (Callable): Function to run
    """
    sleep(0.1)
    func(*args, **kwargs)


_description = '''A Slack command to handle common D&D tasks'''


def assemble_parser(modules: Sequence[InteractionModule]) -> NoExitParser:
    """Generate the argument parser and interaction models

    Args:
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
        subparser = subparsers.add_parser(module.name,
                                          description=module.description,
                                          help=module.help_string,
                                          add_help=True)
        module.register_argparse(subparser)
        subparser.set_defaults(interact=module.interact)

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
    logger.debug(f'Command was from user {payload.user_id} on {payload.channel_id}')
    if payload.command != "/modron":
        if payload.command.lower() == '/roll':
            # Special case for /roll
            payload.text = f'roll {payload.text}'
            logger.info('Caught special case for /roll slash command. Changed it to /modron roll')
        elif payload.command.startswith('/m'):
            # Determine the sub command name
            subcommand = payload.command[2:]
            payload.text = f'{subcommand} {payload.text}'
            logger.info(f'Expanded shortcut command to the longer-form "/modron {payload.text}')
        else:
            return {
                'text': 'ERROR: your command is not supported by Modron yet :('
            }

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
