""""Configuration details"""
import os
import logging
from typing import Optional, List, Dict, Tuple

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Defaults for MAB's NPC generator
_RACE_TIER_WEIGHTS = [50, 10, 3, 2]
_RACE_DISTRIBUTION = {
    'default': [
        ['human'],
        ['dwarf', 'elf', 'halfling', 'half-orc'],
        ['gnome', 'half-elf'],
        ['dragonborn', 'tiefling']
    ],
    'AAA': [
        ['tiefling'],
        ['dwarf', 'human', 'halfling', 'gnome'],
        ['half-orc', 'half-elf'],
        ['dragonborn', 'elf']
    ]
}
_RELATIONSHIP_DIST = [
    (1, 'actively breaking up/single forever'),
    (5, 'bad breakup recently'),
    (10, 'single and fine with it'),
    (14, 'longer relationship'),
    (19, 'married/partnered'),
    (20, 'so in effin\' in love')
]
#  Following Xanathar's
_AGE_DISTRIBUTION = [
    (20, '20 years or younger'),
    (60, '21-30 years'),
    (70, '31-40 years'),
    (85, '41-50 years'),
    (95, '51-60 years'),
    (100, '60+ years')
]


class ModronConfig(BaseModel):
    """Configuration items that customize Modron for a certain campaign

    We assume that one campaign per Slack domain"""

    # Server state
    state_path: str = Field(os.path.join(os.path.dirname(__file__), '..', 'modron_state.yml'),
                            help='Path to the Modron state YAML file')

    # Reminders
    reminder_channel: str = Field('ic_all', help='Channel on which to post reminders')
    watch_channels: str = Field(r'ic_(?!mezu_gm)', help='Regex define which channels to watch for activity')

    # Backing up messages
    backup_path: str = Field('backup', help='Path to directory where channel text will be stored')
    backup_channels: str = Field(r'^(ic_.*|open_questions)$', help='Regex defining which channels to backup')

    # Logging dice rolls
    dice_log: Optional[str] = Field('dice_rolls.csv', help='Path where Modron should write the result of dice rolls. '
                                                           'Set to ``None`` to disable logging')
    dice_skip_channels: List[str] = Field(['bot_test', 'ooc_discussion'], help="List of channels to omit from logging")

    # Character sheets
    character_sheet_path: str = Field('characters', help='Path to a directory with the character sheet YAML files')

    # NPC generator
    # TODO (wardlt): Build a more robust validator for each of these fields
    npc_race_weights: List[float] = Field(_RACE_TIER_WEIGHTS, help="Weights for different probability tiers",
                                          min_items=4, max_items=4)
    npc_race_dist: Dict[str, List[List[str]]] = Field(
        _RACE_DISTRIBUTION, help='Common races for different locations. Each location is defined by a list of '
                                 'four different tears. The first tier is the most prevalent and has a single race. '
                                 'The second, third and fourth tiers have 4, 2 and 2 members, respectively.'
    )
    npc_relationship_dist: List[Tuple[int, str]] = Field(
        _RELATIONSHIP_DIST, help='Distribution of relationship outcomes. Each item in the list is a tuple '
                                 'where the first member is the minimum roll needed to achieve this status '
                                 'and the second is a description of that status. The generator rolls a d20 '
                                 'and the selects the item with the largest minimum roll that is less than '
                                 'or equal to the dice roll.'
    )
    npc_age_dist: List[Tuple[int, str]] = Field(
        _AGE_DISTRIBUTION, help='Distribution of character ages. Each item in the list is a tuple where '
                                'the first member is the minimum roll needed for the age and the second member '
                                'is an age range. The generator rolls percentile dice and the selects the item'
                                ' with the largest minimum roll that is less than or equal to the dice roll.'
    )


def get_config() -> ModronConfig:
    if 'MODRON_CONFIG' in os.environ:
        cfg_path = os.environ['MODRON_CONFIG']
        logger.info(f'Loading Modron config from {cfg_path}')
        with open(cfg_path) as fp:
            return ModronConfig.parse_obj(yaml.load(fp, yaml.SafeLoader))
    else:
        return ModronConfig()
