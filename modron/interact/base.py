"""Base class for interaction modules"""

from argparse import ArgumentParser, Namespace
from typing import Dict

from pydantic import BaseModel, Field, AnyHttpUrl

from modron.slack import BotClient


class SlashCommandPayload(BaseModel):
    """Definition for the payload from a slash command"""

    command: str = Field(..., description='Command that was typed in to trigger this request')
    text: str = Field(..., description='Part of the Slash Command after the command itself')
    response_url: AnyHttpUrl = Field(..., description='A temporary webhook URL that you can use to'
                                                      ' generate messages responses')
    trigger_id: str = Field(..., description='A temporary ID that will let your app open a modal')
    user_id: str = Field(..., description='The ID of the user who triggered the command')
    channel_id: str = Field(..., description='Name of the channel from which this command was triggered')
    team_id: str = Field(..., description='Name fo the team from which this command originated')


class InteractionModule:
    """Base class for actions that Modron can perform.

    This class defines an interface for calling these actions
    and for registering this action in the argument parser

    See `documentation on slash commands <https://api.slack.com/interactivity/slash-commands>`_
    for how to respond to a slack command. Note the part about replying immediately
    is not applicable here. The :meth:`interact` will be executed in a Thread
    while the function calling the interaction method returns a "received" method
    back to Slack.
    """

    def __init__(self, clients: Dict[str, BotClient], name: str, help_string: str, description: str):
        """
        Args:
             clients: Map of team ID to appropriately-authenticated client
             name (str): Name of the interaction module, defines the subcommand name
             help_string (str): Short-form name description of the module. Used in the root parser description
             description (str): Long-form description of the module. Used in its detailed home command
        """
        self.clients = clients
        self.name = name
        self.help_string = help_string
        self.description = description

    def register_argparse(self, parser: ArgumentParser):
        """Define a subparser for this class

        Args:
            parser (ArgumentParser): Argument parser to modify
        """
        raise NotImplementedError()

    def interact(self, args: Namespace, payload: SlashCommandPayload):
        """Perform an interaction given the details of a message

        Args:
            args (Namespace): Parsed arguments for the command
            payload (SlashCommandPayload): Full description of the slash command
        """
        raise NotImplementedError()
