"""Base class for interaction modules"""
from argparse import ArgumentParser, Namespace
import logging

from discord.ext.commands import Context

from modron.interact import NoExitParser, NoExitParserError

logger = logging.getLogger(__name__)


class InteractionModule:
    """Base class for actions that Modron can perform.

    This class defines an interface for calling these actions
    and for registering this action in the argument parser.

    When registering the argument parser, you may not use the words ``interact`` or
    ``subcommand`` in your arguments because they are used by the main parser.

    See `documentation on slash commands <https://api.slack.com/interactivity/slash-commands>`_
    for how to respond to a slack command. Note the part about replying immediately
    is not applicable here. The :meth:`interact` will be executed in a Thread
    while the function calling the interaction method returns a "received" method
    back to Slack.
    """

    def __init__(self, name: str, help_string: str, description: str):
        """
        Args:
             name (str): Name of the interaction module, defines the subcommand name
             help_string (str): Short-form name description of the module. Used in the root parser description
             description (str): Long-form description of the module. Used in its detailed home command
        """
        self.name = name
        self.help_string = help_string
        self.description = description

        # Build the parser for this class
        self.parser = NoExitParser(description=self.description, prog=f'/{name}')
        self.register_argparse(self.parser)

    def register_argparse(self, parser: ArgumentParser):
        """Define a subparser for this class

        Args:
            parser (ArgumentParser): Argument parser to modify
        """
        raise NotImplementedError()

    async def command(self, context: Context, *args):
        """Command interface to Discord bot interface

        Args:
            context: Context of the command invocation
            args: List of arguments
        """
        try:
            args = self.parser.parse_args(args)
        except NoExitParserError as exc:
            logger.info(f'Parser raised an exception. Message: {exc.error_message}')
            await context.send(exc.make_message())
        await self.interact(args, context)

    async def interact(self, args: Namespace, context: Context):
        """Perform an interaction given the details of a message

        Args:
            args (Namespace): Parsed arguments for the command
            context (SlashCommandPayload): Full description of the slash command
        """
        raise NotImplementedError()
