"""Saving and using information about characters"""

import os
from enum import Enum
from typing import Dict, List, Tuple

import yaml
from pydantic import BaseModel, Field, validator

from modron.config import get_config


def _compute_mod(score: int) -> int:
    """Compute a mod given an ability score

    Args:
        score (int): Ability score
    Returns:
        (int) Modifier for that score
    """
    return score // 2 - 5


class Ability(str, Enum):
    """Character abilities"""
    STR = 'strength'
    DEX = 'dexterity'
    CON = 'constitution'
    INT = 'intelligence'
    WIS = 'wisdom'
    CHA = 'charisma'

    @classmethod
    def match(cls, name: str) -> 'Ability':
        """Match a name to known ability

        Args:
            name (str): Name to be matched
        Returns:
            (Ability) Standardized version of that name
        """
        name = name.lower()
        matched_abilities = [x for x in cls.__members__.values() if x.startswith(name)]
        assert len(matched_abilities) == 1, f"Unrecognized ability: {name}"
        return matched_abilities[0]


_5e_skills = {
    'acrobatics': Ability.DEX, 'animal handling': Ability.WIS, 'arcana': Ability.INT, 'athletics': Ability.STR,
    'deception': Ability.CHA, 'history': Ability.INT, 'insight': Ability.WIS, 'intimidation': Ability.CHA,
    'investigation': Ability.INT, 'medicine': Ability.WIS, 'nature': Ability.INT, 'perception': Ability.WIS,
    'performance': Ability.CHA, 'persuasion': Ability.CHA, 'religion': Ability.INT, 'slight of hand': Ability.DEX,
    'stealth': Ability.DEX, 'survival': Ability.WIS
}


class Alignment(str, Enum):
    """Possible alignments"""
    LAWFUL_GOOD = 'lawful good'
    GOOD = 'good'
    CHAOTIC_GOOD = 'chaotic good'
    LAWFUL_NEUTRAL = 'lawful'
    NEUTRAL = 'neutral'
    CHAOTIC_NEUTRAL = 'chaotic neutral'
    LAWFUL_EVIL = 'lawful evil'
    EVIL = 'evil'
    CHAOTIC_EVIL = 'chaotic evil'


_class_hit_die = {
    'barbarian': 12, 'bard': 8, 'cleric': 8, 'druid': 8, 'fighter': 10, 'monk': 8, 'paladin': 10,
    'ranger': 10, 'rogue': 8, 'sorcerer': 6, 'warlock': 8, 'wizard': 6
}
"""Hit die for each 5E class"""


class Character(BaseModel):
    """A D&D 5th edition character sheet, in Python form.

    This object stores only the mechanics-related aspects of a character sheet
    that remained fixed between level ups. For example, we store the hit point
    maximum but not the current hit points and the skill ist but not the languages."""

    # Basic information about the character
    name: str = Field(..., description='Name of the character')
    player: str = Field(None, description='Slack user ID of the player')
    classes: Dict[str, int] = Field(..., description='Levels in different classes')
    background: str = Field(None, description='Character background')
    race: str = Field(None, description='Race of the character')
    alignment: Alignment = Field(..., description='Alignment for the character')

    # Attributes
    strength: int = Field(..., description='Physical strength of the character', ge=0)
    dexterity: int = Field(..., description='Gracefulness of the character', ge=0)
    constitution: int = Field(..., description='Resistance to physical adversity', ge=0)
    intelligence: int = Field(..., description='Ability to apply knowledge and skills', ge=0)
    wisdom: int = Field(..., description='Aptitude towards using knowledge to make good decisions', ge=0)
    charisma: int = Field(..., description='Proficiency with bringing people to agreement with you', ge=0)

    # Combat attributes
    speed: int = Field(30, description='Speed in feet per round. Default: 30')
    armor_class: int = Field(..., description='Resistance to physical attacks.')  # Eventually make derived
    hit_points: int = Field(..., description='Maximum number of hit points')

    # Abilities
    saving_throws: List[Ability] = Field(..., description='Saving throws for which the character is proficient')
    custom_skills: Dict[str, Ability] = Field(dict(), description='Skills not included in 5e. '
                                                                  'Dictionary of skill names and associated ability')
    proficiencies: List[str] = Field(..., description='Names of skills in which the characters is proficient.')
    expertise: List[str] = Field([], description='Skills in which the character is an expert')

    @classmethod
    def from_yaml(cls, path: str) -> 'Character':
        with open(path) as fp:
            data = yaml.load(fp, yaml.SafeLoader)
            return cls.parse_obj(data)

    # Validators for different fields
    @validator('proficiencies', 'expertise', each_item=True)
    def _val_lowercase(cls, v: str) -> str:
        return v.lower()

    @validator('custom_skills', 'classes')
    def _val_dicts(cls, v: dict):
        """Makes keys for dictionaries """
        return dict((k.lower(), v) for k, v in v.items())

    # Derived quantities, such as modifiers
    @property
    def strength_mod(self) -> int:
        return _compute_mod(self.strength)

    @property
    def dexterity_mod(self) -> int:
        return _compute_mod(self.dexterity)

    @property
    def constitution_mod(self) -> int:
        return _compute_mod(self.constitution)

    @property
    def intelligence_mod(self) -> int:
        return _compute_mod(self.intelligence)

    @property
    def wisdom_mod(self) -> int:
        return _compute_mod(self.wisdom)

    @property
    def charisma_mod(self) -> int:
        return _compute_mod(self.charisma)

    @property
    def level(self) -> int:
        return sum(self.classes.values())

    @property
    def proficiency_bonus(self) -> int:
        return (self.level - 1) // 4 + 2

    @property
    def initiative(self):
        return self.initiative

    def get_hit_die(self) -> Dict[str, int]:
        """Maximum hit die, computed based on class

        Returns:
            (dict) Where key is the hit die and value is the number
        """
        output = {}
        for cls, num in self.classes.items():
            hit_die = f'd{_class_hit_die[cls]}'
            if hit_die not in output:
                output[hit_die] = num
            else:
                output[hit_die] += num
        return output

    # Skills and checks
    def save_modifier(self, ability: str) -> int:
        """Get the modifier for a certain save type of save

        Args:
            ability (str): Ability to check. You can use the full name or
                the first three letters. Not case-sensitive
        Returns:
             (int) Modifier for the roll
        """

        # Get the modifier
        mod = self.ability_modifier(ability)

        # Add any proficiency bonus
        if ability.lower() in self.saving_throws:
            mod += self.proficiency_bonus
        return mod

    def ability_modifier(self, ability: str) -> int:
        """Get the modifier for a certain ability

        Args:
            ability (str): Ability to check. You can use the full name or
                the first three letters. Not case-sensitive
        Returns:
            (int) Modifier for the roll
        """
        # Attempt to match the ability to the pre-defined list
        ability = ability.lower()
        matched_ability = Ability.match(ability)

        # Look up the ability modifier
        return getattr(self, f'{matched_ability}_mod')

    def skill_modifier(self, name: str) -> int:
        """Get the skill modifier for a certain skill

        First looks in custom skill list and then in the standard 5e skills.
        In this way, you can define a character to use a non-standard ability
        for a certain skill (as in how Monks can use Wisdom for many checks).

        Args:
            name (str): Name of the skill. Not case sensitive
        """
        name_lower = name.lower()

        # Determine which ability modifier to use
        if name_lower in self.custom_skills:
            ability = self.custom_skills[name_lower]
        elif name_lower in _5e_skills:
            ability = _5e_skills[name_lower]
        else:
            raise ValueError(f'Unrecognized skill: {name}')
        mod = getattr(self, f'{ability}_mod')

        # Add proficiency or expertise
        if name_lower in self.expertise:
            return mod + self.proficiency_bonus * 2
        elif name_lower in self.proficiencies:
            return mod + self.proficiency_bonus
        else:
            return mod

    def lookup_modifier(self, check: str) -> int:
        """Get the modifier for certain roll

        Args:
            check (str): Description of which check to make
        Returns:
            (int) Modifier for the d20 roll
        """

        # Make it all lowercase
        check = check.lower()
        words = check.split(" ")

        # Save
        if 'save' in words:
            return self.save_modifier(words[0])

        # Ability check
        try:
            return self.ability_modifier(check)
        except AssertionError:
            pass  # and try something else

        # Skill
        return self.skill_modifier(check)


def list_available_characters(team_id: str, user_id: str) -> List[str]:
    """List the names of character sheets that are available to a user

    Args:
        team_id (str): ID of the Slack workspace
        user_id (str): ID of the user in question
    Returns:
        ([str]): List of characters available to this player
    """

    # Get all characters for this team
    config = get_config()
    sheets = config.list_character_sheets(team_id)

    # Return only the sheets
    return [
        os.path.basename(s)[:-4]  # Remove the ".yml"
        for s in sheets
        if Character.from_yaml(s).player == user_id
    ]


def load_character(team_id: str, name: str) -> Character:
    """Load a character sheet

    Arg:
        team_id (str): ID of the Slack workspace
        name (str): Name of the character
    Returns:
        (Character) Desired character sheet
    """

    # Get the path to the character sheet
    config = get_config()
    return Character.from_yaml(config.get_character_sheet_path(team_id, name))
