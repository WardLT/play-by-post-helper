"""Saving and using information about characters"""
import json
import re
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import yaml
from pydantic import BaseModel, Field, validator

from modron.config import config


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
    'performance': Ability.CHA, 'persuasion': Ability.CHA, 'religion': Ability.INT, 'sleight of hand': Ability.DEX,
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
    'artificer': 8, 'barbarian': 12, 'bard': 8, 'cleric': 8, 'druid': 8, 'fighter': 10, 'monk': 8, 'paladin': 10,
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
    player: int = Field(None, description='Discord user ID of the player')
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
    speed: int = Field(30, description='Speed in feet per round')
    armor_class: int = Field(..., description='Resistance to physical attacks.')  # Eventually make derived
    current_hit_points: Optional[int] = Field(..., description='Current hit points. Does not include temporary', ge=0)
    hit_points: int = Field(..., description='Maximum number of hit points', gt=0)
    temporary_hit_points: int = Field(0, description='Amount of temporary hit points.', ge=0)
    hit_points_adjustment: int = Field(0, description='Adjustments to the hit point maximum. '
                                                      'Can be positive or negative')

    # Abilities
    saving_throws: List[Ability] = Field(..., description='Saving throws for which the character is proficient')
    custom_skills: Dict[str, Ability] = Field(dict(), description='Skills not included in 5e. '
                                                                  'Dictionary of skill names and associated ability')
    proficiencies: List[str] = Field(..., description='Names of skills in which the characters is proficient.')
    expertise: List[str] = Field([], description='Skills in which the character is an expert')

    # Conveniences
    roll_aliases: Dict[str, str] = Field(default_factory=dict,
                                         description='User-defined map of skill to rolls. Rolls can '
                                                     'be a combination of dice, additive multipliers and traits. '
                                                     'For example, "4d6+str+2" or "1d20+proficiency"')

    @classmethod
    def from_yaml(cls, path: str) -> 'Character':
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
            yaml.dump(data, fp, indent=2)

    # Validators for different fields
    @validator('proficiencies', 'expertise', each_item=True)
    def _val_lowercase(cls, v: str) -> str:
        return v.lower()

    @validator('custom_skills', 'classes', 'roll_aliases')
    def _val_dicts(cls, v: dict):
        """Makes keys for dictionaries"""
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
    def initiative(self) -> int:
        output = self.dexterity_mod
        if self.classes.get('bard', 0) >= 2:
            output += self.proficiency_bonus // 2
        return output

    @property
    def total_hit_points(self) -> int:
        """Current hit point amount, including temporary hit points"""
        return self.current_hit_points + self.temporary_hit_points

    @property
    def current_hit_point_maximum(self) -> int:
        """Current hit point maximum"""
        return self.hit_points + self.hit_points_adjustment

    def heal(self, amount: int):
        """Heal the character by a certain amount

        Args:
            amount (int): Amount of healing
        """
        assert amount >= 0, "Amount must be nonnegative"
        if self.current_hit_points is None:
            self.full_heal()
        self.current_hit_points += amount
        self.current_hit_points = min(self.current_hit_points, self.current_hit_point_maximum)

    def harm(self, amount: int):
        """Apply damage to this character

        Args:
            amount (int): Amount of damage
        """
        assert amount >= 0, "Damage must be nonnegative"
        if self.current_hit_points is None:
            self.full_heal()

        # Damage hits the temporary first
        amount_to_temp = min(self.temporary_hit_points, amount)
        amount_to_base = amount - amount_to_temp
        self.temporary_hit_points -= amount_to_temp

        # Subtract off the remaining damage from the base hit points
        self.current_hit_points -= amount_to_base
        self.current_hit_points = max(0, self.current_hit_points)

    def full_heal(self):
        """Heal character up to hit point maximum"""
        self.current_hit_points = self.current_hit_point_maximum

    def grant_temporary_hit_points(self, amount: int):
        """Grant temporary hit points

        Args:
            amount: Amount of HP to give to the character
        """
        assert amount > 0, "Amount must be positive"
        self.temporary_hit_points += amount

    def remove_temporary_hit_points(self):
        """Remove all temporary hit points"""
        self.temporary_hit_points = 0

    def adjust_hit_point_maximum(self, amount: int):
        """Apply a change to the hit point maximum

        Args:
            amount: Amount to change the HP maximum
        """
        self.hit_points_adjustment += amount

        # Make sure the hit point maximum is zero or more
        self.hit_points_adjustment = max(-self.hit_points, self.hit_points_adjustment)

        # Make sure the hit points stays below the maximum
        self.current_hit_points = min(
            self.current_hit_point_maximum,
            self.current_hit_points
        )

    def reset_hit_point_maximum(self):
        """Remove any adjustments to the hit point maximum"""
        self.hit_points_adjustment = 0

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

        # Match the name of the ability
        matched_ability = Ability.match(ability)

        # Add any proficiency bonus
        if matched_ability.lower() in self.saving_throws:
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
            name (str): Name of the skill. Not case-sensitive
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
        elif self.classes.get('bard', 0) >= 2:
            return mod + self.proficiency_bonus // 2
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

        # Get the proficiency bonus
        if len(words) == 1:
            word = words[0]
            if word in ['initiative', 'init']:
                return self.initiative
            elif word in ['proficiency', 'prof']:
                return self.proficiency_bonus

        # Start with initiative
        if words == ['initiative'] or words == ['init']:
            return self.initiative

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

    def get_skills_by_ability(self, ability: str) -> Dict[str, str]:
        """List out the skills for this character that use a certain base ability

        Args:
            ability: Name of the ability
        Returns:
            Dictionary of the skill mapped to the level of skill (expert, proficient, untrained)
        """

        # Match the ability
        matched_ability = Ability.match(ability)

        # Loop over the 5e skills
        matched_skills = [skill for skill, attr in _5e_skills.items() if attr == matched_ability]

        # Match the custom skills
        matched_skills.extend([
            skill for skill, attr in self.custom_skills.items() if attr == matched_ability
        ])

        # Return the outputs
        output = {}
        for skill in matched_skills:
            if skill in self.proficiencies:
                output[skill] = "proficient"
            elif skill in self.expertise:
                output[skill] = "expert"
            else:
                output[skill] = "untrained"
        return output

    def substitute_modifiers(self, roll_description: str) -> str:
        """Substitute then combine the modifiers in a roll description

        Roll descriptions can combine dice (e.g., "3d10")
        skill modifiers (e.g., "proficiency," "strength"),
        and integers.

        Algorithm:
            1. Split roll description based on addition or subtraction markers
            2. Resolve skill modifiers
            3. Combine into a single dice roll description
        Returns:
            String describing a dice roll
        """

        # Split based on +-
        split_description = re.split('([+-])', roll_description)

        # Prepend a + sign if none provided
        if split_description[0] not in ['-', '+']:
            split_description.insert(0, '+')

        # Separate dice and
        dice = []
        mods = []
        for sign, part in zip(split_description[::2], split_description[1::2]):
            # Convert sign to +/-1, part to lower case
            sign = 1 if sign == "+" else -1
            part = part.strip()

            if part.isdigit():  # It is an integer
                mods.append(sign * int(part))
            elif 'd' in part and any(x.isdigit() for x in part):  # It contains at least one digit and d
                dice.append(part)
            else:  # Assume it is a modifier
                mods.append(sign * self.lookup_modifier(part))

        # Combine everything together into a single dice roll
        return f'{"+".join(dice)}{sum(mods):+d}'


def list_available_characters(guild_id: int, user_id: int) -> List[str]:
    """List the names of character sheets that are available to a user

    Args:
        guild_id: Associated guild
        user_id: ID of the user in question
    Returns:
        List of characters available to this player
    """

    # Return only the sheets for this player
    return [
        s.name[:-4]  # Remove the ".yml"
        for s in config.list_character_sheets(guild_id)
        if Character.from_yaml(s).player == user_id
    ]


def load_character(guild_id: int, name: str) -> Tuple[Character, Path]:
    """Load a character sheet

    Arg:
        guild_id: Associated guild
        name: Name of the character
    Returns:
        - Desired character sheet
        - Absolute path to the character sheet, in case you must save it later
    """
    sheet_path = config.get_character_sheet_path(guild_id, name)
    return Character.from_yaml(sheet_path), sheet_path.absolute()
