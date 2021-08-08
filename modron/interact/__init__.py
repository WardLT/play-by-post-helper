"""Functions that make Modron interactive

Holds logic of how Modron should respond a certain direct message"""
import logging
from typing import Sequence, NoReturn

from discord.ext.commands import Context, Command

from modron.bot import ModronClient
from modron.interact._argparse import NoExitParserError, NoExitParser
from modron.interact.base import InteractionModule

logger = logging.getLogger(__name__)


_description = '''A Discord command to handle common D&D tasks'''


def attach_commands(bot: ModronClient, modules: Sequence[InteractionModule]) -> NoExitParser:
    """Generate the argument parser and interaction models,
    define them as inputs to commands in the

    Args:
        bot:
        modules ([InteractionModule]): List of modules to use for this parser
    Returns:
        (NoExitParser): Parser to use for receiving commands
    """

    # Step one: create commands for each of the individual modules
    for module in modules:
        cmd = Command(module.command, name=module.name)
        bot.add_command(cmd)

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


async def handle_generic_slash_command(context: Context, parser: NoExitParser) -> NoReturn:
    """Respond to a generic "/modron" slash command

    Args:
        context (SlashCommandPayload): Slash command data sent from Slack
        parser (ArgumentParser): Parser to use to understand command
    """

    # Expand shortcut commands
    logger.info(f'Received command: {context.args}')
    logger.debug(f'Command was from user {context.author.name} on {context.channel.name}')

    # Parse the command
    try:
        args = parser.parse_args(context.args)
    except NoExitParserError as exc:
        logger.info(f'Parser raised an exception. Message: {exc.error_message}')
        await context.send(exc.make_message())
        return

    # If there is not an interact command, return help message
    if not hasattr(args, 'interact'):
        parser.print_help()
        msg = parser.text_buffer.getvalue()
        logger.info(f'Sending some help messages back. {repr(msg[:64])}...{len(msg)} char')
        return

    await args.interact(args, context)
