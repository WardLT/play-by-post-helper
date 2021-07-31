"""Store and retrieve state about Modron

Modron uses an object that we read to and from disk in YAML format.
Transactions should be infrequent enough and queries simple enough
that performance requirements will not require a formal database.

Using YAML to store state on disk has the advantage of it being easy to
assess and alter the server state from the command line.
"""
from datetime import datetime
import json
from typing import Dict

import yaml
from pydantic import BaseModel, Field

from modron.config import get_config


config = get_config()


class ModronState(BaseModel):
    """Holder for elements of Modron's configuration that can change during runtime
    or need to be persistent across restarts"""

    reminder_time: Dict[int, datetime] = Field(None, description='Next time to check if a reminder is needed')

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
