""""Configuration details"""
import os
import logging
from glob import glob
from datetime import timedelta
from typing import List, Dict, Tuple, Optional

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


class TeamConfig(BaseModel):
    """Configuration settings specific for a Slack team"""

    name: str = Field(..., help='Name of the Slack team to be used internally by Modron. '
                                'Must be unique from the other teams and should be more memorable than '
                                'the unique ID generated by Slack.')

    # Reminders
    reminders: bool = Field(True, help='Whether to post inactivity reminders')
    reminder_channel: str = Field('ic_all', help='Channel on which to post reminders')
    watch_channels: str = Field(r'^ic_.*', help='Regex define which channels to watch for activity')
    allowed_stall_time: timedelta = Field(timedelta(days=1),
                                          description='How long to wait for activity before issuing reminders')

    # Backing up messages
    backup_channels: Optional[str] = Field(r'^ic_.*', help='Regex defining which channels to backup')

    # Logging dice rolls
    dice_log: bool = Field(True, help='Whether to log dice rolls for this team')
    dice_skip_channels: List[str] = Field(['bot_test', 'ooc_discussion'], help="List of channels to omit from logging")

    # Character sheets
    character_sheet_path: str = Field('characters', help='Path to a directory with the character sheet YAML files')


class ModronConfig(BaseModel):
    """Configuration items that customize Modron's behavior"""

    # Paths to key files and directories
    state_path: str = Field(os.path.join(os.path.dirname(__file__), '..', 'modron_state.yml'),
                            help='Path to the Modron state YAML file')
    dice_log_dir: str = Field('dice-logs', help='Path to where the dice logs are stored. One per channel, '
                                                'labelled with name of team defined in this config file.')
    backup_dir: str = Field('backup', help='Path to where to store the backup. Each team will get its own '
                                           'subdirectory')
    character_dir: str = Field('characters', help='Path to the character sheets. Each team has its own subdirectory')
    credentials_dir: str = Field('creds', help='Path to the credentials for third-party (i.e., non-Slack) apps')

    # Miscellaneous options
    gdrive_backup_folder: str = Field('1OmFkSgRvBr3JeWCnOWOaHBiEX5T-AR_V',
                                      help='Where to upload folders on Google drive. Expects a Google Drive folder ID')

    # Team-specific options
    team_options: Dict[int, TeamConfig] = Field({}, help='Settings for the different Slack teams configured to '
                                                         'work with Modron. Key is the Slack team ID')

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

    def get_backup_dir(self, team_id: str) -> str:
        """Get the path to the directory that holds backup files for a certain team

        Args:
            team_id: Name of the team
        Returns:
            Path to the backup directory
        """
        return os.path.join(self.backup_dir, self.team_options[team_id].name)

    def get_dice_log_path(self, team_id: str) -> str:
        """Get the path to the dice log for a certain team

        Args:
            team_id: Name of the team
        Returns:
            Path to the log
        """
        return os.path.join(self.dice_log_dir, f'{self.team_options[team_id].name}.csv')

    def list_character_sheets(self, team_id: str) -> List[str]:
        """List all of paths to the character sheets for a certain workspace

        Args:
            team_id (str): Name of the team
        Returns:
            ([str]): List paths to all of the character sheets
        """

        team_name = self.team_options[team_id].name
        paths = glob(os.path.join(self.character_dir, team_name, '*.yml'))
        return paths

    def get_character_sheet_path(self, team_id: str, name: str) -> str:
        """Get the path to a certain character sheet

        Args:
            team_id (str): ID of the Slack team
            name (str): Name of the character

        Returns:
            (str): Path to the character sheet
        """
        team_name = self.team_options[team_id].name
        return os.path.join(self.character_dir, team_name, f'{name}.yml')

    def get_gdrive_credentials_path(self) -> str:
        """Get the path to the Google Drive credentials,
        which are stored as a pickle file"""

        return os.path.join(self.credentials_dir, 'gdrive', 'token.pickle')


def get_config() -> ModronConfig:
    cfg_path = os.environ.get('MODRON_CONFIG', os.path.join(os.path.dirname(__file__), '..', 'modron_config.yml'))
    if os.path.isfile(cfg_path):
        logger.info(f'Loading Modron config from {cfg_path}')
        with open(cfg_path) as fp:
            return ModronConfig.parse_obj(yaml.load(fp, yaml.SafeLoader))
    else:
        logger.info('Creating default configuration')
        return ModronConfig()
