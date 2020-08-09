"""Get information about a specific character"""
from argparse import Namespace, ArgumentParser
from typing import Dict
import logging

import requests

from modron.interact import SlashCommandPayload
from modron.interact.base import InteractionModule
from modron.characters import list_available_characters, load_character, Character
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

_hp_description = '''Keep track of the HP for a character

This command can be used to get current HP, apply damage or healing, or
make temporary changes to the HP'''


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

        # Add the "hp" command
        hp_parser = subparsers.add_parser('hp', help='Display and keep track of character HP',
                                          description=_hp_description)
        hp_subparsers = hp_parser.add_subparsers(description='Available options for tracking HP', dest='hp_subcommand')

        heal_parser = hp_subparsers.add_parser('heal', help='Apply healing to a character')
        heal_parser.add_argument('amount', help='Amount of healing. Can be an integer or "full".')

        harm_parser = hp_subparsers.add_parser('harm', help='Apply damage to a character')
        harm_parser.add_argument('amount', help='Amount of damage. Must be an integer.', type=int)

        temp_parser = hp_subparsers.add_parser('temp', help='Grant temporary it points')
        temp_parser.add_argument('amount', help='Amount of change, or "reset" to change the temporary back to zero')

        max_parser = hp_subparsers.add_parser('max', help='Adjust hit point maximum')
        max_parser.add_argument('amount', help='Amount of change, or "reset" to change the temporary back to zero')

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
        sheet, sheet_path = load_character(payload.team_id, character)
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
        elif args.char_subcommand == "hp":
            return self._run_hp_subcommand(args, payload, sheet, sheet_path)
        else:
            raise ValueError(f'Subcommand {args.char_subcommand} not yet implemented')

    def _run_hp_subcommand(self, args: Namespace, payload: SlashCommandPayload, sheet: Character, sheet_path: str):
        """Process an HP subcommand

        Args:
            args: Parsed slash command
            payload: Slash command payload
            sheet: Character sheet
            sheet_path: Path to the character sheet
        """

        # Make any changes
        change_msg = ''
        if args.hp_subcommand is None:
            logger.info(f'No changes. Just printing out the HP for {sheet.name}')
        elif args.hp_subcommand == "heal":
            if args.amount.lower() == "full":
                sheet.full_heal()
                change_msg = f"Healed back to the hit point maximum of {sheet.current_hit_point_maximum}."
                logger.info(f"Fully healed {sheet.name} back to {sheet.current_hit_points}")
            else:
                try:
                    amount = int(args.amount)
                except ValueError:
                    logger.info(f'Parse error for heal amount. Input: "{args.amount}"')
                    payload.send_reply(f'Could not parse amount: "{args.amount}"')
                    return

                change_msg = f"Healed {amount} hit points."
                sheet.heal(amount)
                logger.info(f'Healed {sheet.name} {amount} hit points')
        elif args.hp_subcommand == "harm":
            try:
                amount = int(args.amount)
            except ValueError:
                payload.send_reply(f'Could not parse amount: "{args.amount}"')
                logger.info(f'Parse error for harm amount. Input: "{args.amount}"')
                return

            sheet.harm(amount)
            change_msg = f"Took {amount} hit points of damage."
            if sheet.total_hit_points == 0:
                change_msg += f" **{sheet.name} are now unconscious!**"
            logger.info(f'Damaged {sheet.name} {amount} hit points')
        elif args.hp_subcommand == "temp":
            if args.amount.lower() == "reset":
                sheet.remove_temporary_hit_points()
                change_msg = 'Removed all temporary hit points'
                logger.info(change_msg)
            else:
                try:
                    amount = int(args.amount)
                except ValueError:
                    payload.send_reply(f'Could not parse amount: "{args.amount}"')
                    logger.info(f'Parse error for amount. Input: "{args.amount}"')
                    return

                sheet.grant_temporary_hit_points(amount)
                change_msg = f"Granted {amount} temporary hit points."
                logger.info(change_msg)
        elif args.hp_subcommand == "max":
            if args.amount.lower() == "reset":
                sheet.reset_hit_point_maximum()
                change_msg = 'Reset hit point maximum.'
                logger.info(change_msg)
            else:
                try:
                    amount = int(args.amount)
                except ValueError:
                    payload.send_reply(f'Could not parse amount: "{args.amount}"')
                    logger.info(f'Parse error for amount. Input: "{args.amount}"')
                    return

                sheet.adjust_hit_point_maximum(amount)
                change_msg = f"Adjusted hit point maximum by {amount} hit points."
                logger.info(change_msg)
        else:
            raise ValueError(f'Subcommand {args.hp_subcommand} not yet implemented (Blame Logan)')

        # Save changes to the sheet
        if len(change_msg) > 0:
            sheet.to_yaml(sheet_path)
            logger.info(f'Saved updated sheet to {sheet_path}')

        # Render the status message
        msg = ''
        if len(change_msg) > 0:
            msg += f'{change_msg.strip()}\n\n'
        msg += f'{sheet.name} has {sheet.total_hit_points}/{sheet.current_hit_point_maximum} hit points'
        if sheet.hit_points_adjustment != 0:
            msg += f" including a {sheet.hit_points_adjustment} change to HP maximum"

        payload.send_reply(msg, ephemeral=True)
