"""Minimum requirements for character sheets"""
from abc import ABCMeta
from pathlib import Path
from typing import Union, Dict

import yaml
from pydantic import BaseModel, Field


class Character(BaseModel, metaclass=ABCMeta):
    # Basic character and player information
    player: int = Field(None, description='Discord user ID of the player')
    name: str = Field(..., description='Name of the character')

    # Conveniences
    roll_aliases: Dict[str, Union[int, str]] = Field(
        default_factory=dict,
        description='User-defined map of skill to rolls. Rolls can be a combination of dice, '
                    'additive multipliers and traits. For example, "4d6+str+2" or "1d20+proficiency"')

    @classmethod
    def from_yaml(cls, path: Union[str, Path]) -> 'Character':
        """Parse the character sheet from YAML

        Args:
            path: Path to the YAML file
        """
        with open(path) as fp:
            data = yaml.load(fp, yaml.SafeLoader)
            return cls.model_validate(data)

    def to_yaml(self, path: Union[str, Path]):
        """Save character sheet to a YAML file"""

        with open(path, 'w') as fp:
            yaml.safe_dump(self.model_dump(mode='json'), fp, indent=2, sort_keys=False)

    def create_roll(self, ability_name: str) -> str:
        """Generate a roll corresponding to a certain ability name"""
        raise NotImplementedError()

    def describe_ability(self, ability_name: str) -> str:
        """Generate a one-line description of a character's ability"""
        raise NotImplementedError()
