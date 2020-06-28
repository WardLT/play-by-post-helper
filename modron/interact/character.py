"""Get information about a specific character"""
from argparse import Namespace, ArgumentParser
from typing import Dict
import logging

import requests

from modron.interact import SlashCommandPayload
from modron.interact.base import InteractionModule
from modron.characters import list_available_characters, load_character
from modron.slack import BotClient

logger = logging.getLogger(__name__)

_description = '''Handles operations related to character sheets

Allows users to read from or edit character sheets. Common uses will
be to set HP and look up statistics.

You may also use this command to change which character you are playing,
which will dictate the character sheet it reads.
'''

_ability_description = '''Gets the dice and modifier for a certain roll.

Modron will attempt to infer the what you are looking for from the following options:'
- _Ability check_. List the ability and if it is at proficiency. Ex: "dex" or "prof dex" or "dexterity proficiency"
- _Save_. Name the ability (full name or abbreviation is fine)
- _Skill check_. Give the name of the skill'''


class CharacterSheet(InteractionModule):
    """Handles interactions related to a character sheet"""

    def __init__(self, clients: Dict[str, BotClient]):
        super().__init__(clients, name='character', help_string='Work with character sheets',
                         description=_description)

    def register_argparse(self, parser: ArgumentParser):
        # Add a subparser group
        subparsers = parser.add_subparsers(description='Available options for working with characters',
                                           dest='char_subcommand')

        # Add the "ability" command
        ability_parser = subparsers.add_parser('ability', help='Lookup an ability for a character',
                                               description=_ability_description)
        ability_parser.add_argument('name', help='Which ability to look up', nargs='+')

    def interact(self, args: Namespace, payload: SlashCommandPayload):
        # Get the characters available for this player
        available_chars = list_available_characters(payload.team_id, payload.user_id)
        if len(available_chars) == 0:
            logger.info('No character found for this player')
            requests.post(
                payload.response_url,
                json={
                    'text': 'You have not defined a character yet. Talk to Logan.'
                }
            )
            return

        # Determine which character is being played
        assert len(available_chars) == 1, "Modron does not yet support >1 character per user"
        character = available_chars[0]
        sheet = load_character(payload.team_id, character)
        logger.info(f'User {payload.user_id} mapped to character {sheet.name}. Loaded their sheet')

        # Switch on the chosen subcommand
        if args.char_subcommand is None:
            # Return the character sheet
            logger.info('Reminding the user which character they are currently playing')
            payload.send_reply(f'You are playing {sheet.name} (lvl {sheet.level})', ephemeral=True)
        elif args.char_subcommand == "ability":
            ability_name = ' '.join(args.name)
            try:
                modifier = sheet.lookup_modifier(ability_name)
            except ValueError:
                logger.info(f'Modifier lookup failed for "{ability_name}"')
                payload.send_reply(f'Could not find a modifier for "{ability_name}"')
                return
            logger.info(f'Retrieved modifier for {ability_name} rolls: {modifier:+d}')
            payload.send_reply(f'{sheet.name}\'s modifier for {ability_name} is {modifier:+d}', ephemeral=True)
        else:
            raise ValueError(f'Subcommand {args.char_subcommand} not yet implemented')
