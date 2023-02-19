"""Store and retrieve state about Modron

Modron uses an object that we read to and from disk in YAML format.
Transactions should be infrequent enough and queries simple enough
that performance requirements will not require a formal database.

Using YAML to store state on disk has the advantage of it being easy to
assess and alter the server state from the command line.
"""
from datetime import datetime
import json
from typing import Dict, Optional

import yaml
from discord import Message
from pydantic import BaseModel, Field

from modron.config import config


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
            last_time=message.created_at,
            sender=message.author.name,
            channel=message.channel.name,
        )


class ModronState(BaseModel):
    """Holder for elements of Modron's configuration that can change during runtime
    or need to be persistent across restarts"""

    reminder_time: Dict[int, datetime] = Field(None, description='Next time to check if a reminder is needed')
    last_message: Optional[LastMessage] = Field(None, description='Information about the last message')

    @classmethod
    def load(cls, path: str = config.state_path) -> 'ModronState':
        """Load the configuration from disk

        Args:
            path (str): Path to the state as a YML file
        Returns:
            (ModronState) State from disk
        """
        with open(path, 'r') as fp:
            data = yaml.load(fp, yaml.SafeLoader)
            return ModronState.parse_obj(data)

    def save(self, path: str = config.state_path):
        """Save the state to disk in YML format

        Args:
            path (str): Where to save the data
        """
        with open(path, 'w') as fp:
            # Convert to JSON so that it uses Pydantic's conversations of special types
            ready = json.loads(self.json())
            yaml.dump(ready, fp, indent=2)
