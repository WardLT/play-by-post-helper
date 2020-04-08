"""Functions that make Modron interactive

Holds logic of how Modron should respond a certain direct message"""
import shlex
import logging
from io import StringIO
from argparse import ArgumentParser
from typing import Dict, Union, Sequence, Text, NoReturn, Optional, IO

from modron.interact.base import SlashCommandPayload, InteractionModule
from modron.interact.dice_roll import DiceRollInteraction
from modron.slack import BotClient
from modron.utils import escape_slack_characters

logger = logging.getLogger(__name__)


_modules = (DiceRollInteraction,)


class NoExitParserError(Exception):
    """Error when parsing fails.

    Captures the error message and what was printed to screen from the
    parser that threw the error. This allows for the screen output
    from subparsers to be easily accessed by the user, as they will
    be passed along with the exception itself."""

    def __init__(self, parser: 'NoExitParser', error_message: Text,
                 text_output: Text):
        super().__init__()
        self.parser = parser
        self.error_message = error_message
        self.text_output = text_output


class NoExitParser(ArgumentParser):
    """A version of ArgumentParser that does not terminate on exit"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.text_buffer = StringIO()

    def _print_message(self, message: str, file: Optional[IO[str]] = ...) -> None:
        if message:
            self.text_buffer.write(message)
            self.text_buffer.flush()

    def exit(self, status: int = ..., message: Optional[Text] = None) -> NoReturn:
        raise NoExitParserError(self, message, self.text_buffer.getvalue())

    def error(self, message: Text) -> NoReturn:
        raise NoExitParserError(self, message, self.text_buffer.getvalue())


def assemble_parser(client: BotClient, modules: Sequence[InteractionModule.__class__] = _modules) -> NoExitParser:
    """Generate the argument parser and interaction models

    Args:
        client (BotClient): Client to be used by the interaction modules
        modules ([InteractionModule]): List of modules to use for this parser
    Returns:
        (NoExitParser): Parser to use for receiving commands
    """

    # Assemble the root parser
    parser = NoExitParser(description='All of the available actions for Modron', add_help=True, prog='/modron')

    # Register the modules
    subparsers = parser.add_subparsers(title='Available Commands',
                                       description='The different possible ways to interact with Modron',
                                       dest='subcommand')
    for module in modules:
        module_inst = module(client)
        subparser = subparsers.add_parser(module_inst.name,
                                          description=module_inst.description,
                                          help=module_inst.description,
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
            msg = f'<div color="red">{exc.error_message}</div>\n'
        msg += exc.text_output

        return {
            'text': escape_slack_characters(msg),
            'mkdwn': True
        }

    # Run the specified command
    args.interact(args, payload)

    return {"response_type": "in_channel"}
