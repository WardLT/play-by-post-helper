"""Functions that make Modron interactive

Holds logic of how Modron should respond a certain direct message"""
import logging
from functools import partial, update_wrapper
from typing import Sequence

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
    parser = NoExitParser(description=_description, add_help=True, prog='$modron')

    # Register the modules
    subparsers = parser.add_subparsers(title='available commands',
                                       description='The different ways to interact with Modron',
                                       dest='subcommand')
    for module in modules:
        subparser = subparsers.add_parser(module.name,
                                          description=module.description,
                                          help=module.help_string,
                                          add_help=True)
        module.register_argparse(subparser)
        subparser.set_defaults(interact=module.interact)

    # Attach it to the bot
    new_func = partial(handle_generic_command, parser)
    update_wrapper(new_func, handle_generic_command)
    cmd = Command(new_func, name='modron')
    bot.add_command(cmd)

    logger.info(f'Created a parse function with {len(modules)} interaction modules')
    return parser


async def handle_generic_command(parser: NoExitParser, context: Context, *args):
    """Respond to a generic "/modron" slash command

    Args:
        parser: Parser to use to understand command
        context: Slash command data sent from Slack
        args: Arguments passed to the command
    """

    logger.info(f'Received command from user {context.author.name} on {context.channel.name}: {" ".join(args)}')

    # Parse the command
    try:
        args = parser.parse_args(args)
    except NoExitParserError as exc:
        logger.info(f'Parser raised an exception. Message: {exc.error_message}')
        await context.reply(exc.make_message(), delete_after=60)
        return

    # If there is not an interact command, return help message
    if not hasattr(args, 'interact'):
        parser.print_help()
        msg = parser.text_buffer.getvalue()
        logger.info(f'Sending some help messages back. {repr(msg[:64])}...{len(msg)} char')
        await context.reply(msg, delete_after=60)
    else:
        await args.interact(args, context)
