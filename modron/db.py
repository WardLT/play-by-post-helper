"""Store and retrieve state about Modron

Modron uses an object that we read to and from disk in YAML format.
Transactions should be infrequent enough and queries simple enough
that performance requirements will not require a formal database.

Using YAML to store state on disk has the advantage of it being easy to
assess and alter the server state from the command line.
"""
from typing import Dict, Optional, Union
from datetime import datetime
from pathlib import Path
import logging
import json

import yaml
from discord import Message
from pydantic import BaseModel, Field, validator

from modron.characters import Character, load_character, list_available_characters
from modron.config import config
from modron.discord import timestamp_to_local_tz

logger = logging.getLogger(__name__)


class LastMessage(BaseModel):
    """Information about the last message"""

    last_time: datetime = Field(..., description='Time the last message was sent')
    sender: str = Field(..., description='Username of person who sent the last message')
    channel: str = Field(..., description='Name of the channel in which the message was sent')

    @classmethod
    def from_discord(cls, message: Message):
        """Make description from a discord Message object

        Args:
            message: Message to use for configuration
        Returns:
            Message description
        """
        return cls(
            last_time=timestamp_to_local_tz(message.created_at),
            sender=message.author.name,
            channel=message.channel.name,
        )


class ModronState(BaseModel):
    """Holder for elements of Modron's configuration that can change during runtime
    or need to be persistent across restarts"""

    reminder_time: Dict[int, datetime] = Field(None, description='Next time to check if a reminder is needed')
    last_message: Dict[int, LastMessage] = Field(default_factory=dict, description='Information about the last message')
    characters: Dict[int, Dict[int, str]] = Field(default_factory=dict,
                                                  description='Character being played by each player')

    @validator('reminder_time')
    def convert_str_to_int(cls, value: Optional[Dict]):
        if value is not None:
            return dict((int(k), v) for k, v in value.items())
        return dict()

    @classmethod
    def load(cls, path: Union[str, Path] = config.state_path) -> 'ModronState':
        """Load the configuration from disk

        Args:
            path: Path to the state as a YML file
        Returns:
            State from disk
        """
        with open(path, 'r') as fp:
            data = yaml.load(fp, yaml.SafeLoader)
            return ModronState.parse_obj(data)

    def get_active_character(self, guild_id: int, player_id: int) -> tuple[str, Character, Path]:
        """Get the active character for a player

        Args:
            guild_id: Active guild
            player_id: Player id number
        Returns:
            - Short name of the character
            - Character sheet for the active character
            - Path to the character sheet
        """

        # Assemble the dictionary, if needed
        if guild_id not in self.characters:
            logger.info(f'Initializing character dictionary for {guild_id}')
            self.characters[guild_id] = dict()

        # Load the character's sheet already selected are already defined
        if player_id in self.characters[guild_id]:
            choice = self.characters[guild_id][player_id]
        else:
            # Pick one at random
            choice = list_available_characters(guild_id, player_id)[0]
            logger.info(f'Chose a character at random to start with, {choice}')
            self.characters[guild_id][player_id] = choice

        sheet, path = load_character(guild_id, choice)
        return choice, sheet, path

    def save(self, path: Union[str, Path] = config.state_path):
        """Save the state to disk in YML format

        Args:
            path (str): Where to save the data
        """
        with open(path, 'w') as fp:
            # Convert to JSON so that it uses Pydantic's conversations of special types
            ready = json.loads(self.json())
            yaml.dump(ready, fp, indent=2)
