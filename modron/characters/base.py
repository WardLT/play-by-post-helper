"""Minimum requirements for character sheets"""
import json
from abc import ABCMeta
from pathlib import Path
from typing import Union

import yaml
from pydantic import BaseModel, Field


class Character(BaseModel, metaclass=ABCMeta):
    player: int = Field(None, description='Discord user ID of the player')
    name: str = Field(..., description='Name of the character')

    @classmethod
    def from_yaml(cls, path: Union[str, Path]) -> 'Character':
        """Parse the character sheet from YAML

        Args:
            path: Path to the YAML file
        """
        with open(path) as fp:
            data = yaml.load(fp, yaml.SafeLoader)
            return cls.parse_obj(data)

    def to_yaml(self, path: Union[str, Path]):
        """Save character sheet to a YAML file"""

        with open(path, 'w') as fp:
            data = json.loads(self.json())
            yaml.dump(data, fp, indent=2, sort_keys=False)
