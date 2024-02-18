"""Get information about a specific character"""
from argparse import Namespace, ArgumentParser
import logging
from pathlib import Path
from typing import Tuple, Optional

from discord.ext.commands import Context

from modron.db import ModronState
from modron.interact.base import InteractionModule
from modron.characters import list_available_characters, load_character, Character

logger = logging.getLogger(__name__)

_description = '''Handles operations related to character sheets

TBD: You may also use this command to change which character you are playing,
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


def load_sheet(context: Context, character: Optional[str] = None) -> Tuple[Character, Path]:
    """Load the requested character sheet

    Args:
        context: Context from the command
        character: Requested character, optional
    Returns:
        Character sheet for player's character
    """
    # Get the characters available for this player
    available_chars = list_available_characters(context.guild.id, context.author.id)
    if len(available_chars) == 0:
        logger.warning(f'No character found for {context.author.name}')
        raise ValueError('You have not defined a character yet. Talk to Logan.')

    # Determine which character is being played
    if character is not None:
        # Use the user's choice by default
        character = character.lower()
        try:
            sheet, sheet_path = load_character(context.guild.id, character)
            if sheet.player != context.author.id:
                raise ValueError()
        except (FileNotFoundError, ValueError):
            raise ValueError(f'You are not authorized to play: {character}')
    else:
        # Load the state variable if not
        state = ModronState.load()
        _, sheet, sheet_path = state.get_active_character(context.guild.id, context.author.id)
        logger.info(f'User {context.author} mapped to character {sheet.name}. Loaded their sheet')
    return sheet, sheet_path


class CharacterSheet(InteractionModule):
    """Handles interactions related to a character sheet"""

    def __init__(self):
        super().__init__(name='character', help_string='Work with character sheets', description=_description)

    def register_argparse(self, parser: ArgumentParser):
        parser.add_argument('--character', '-c',
                            help='Name of the character whose sheet to load', default=None)

        # Add a subparser group
        subparsers = parser.add_subparsers(description='Available options for working with characters',
                                           dest='char_subcommand')

        # Add the "ability" command
        ability_parser = subparsers.add_parser('ability', help='Lookup an ability for a character',
                                               description=_ability_description)
        ability_parser.add_argument('name', help='Which ability to look up', nargs='+')

        # Add ability to list the available characters and update the current one
        subparsers.add_parser('list', help='List characters available for you to play')

        set_parser = subparsers.add_parser('set', help='Change your default character')
        set_parser.add_argument("choice", help='Name of character you would like to play')

    async def interact(self, args: Namespace, context: Context):
        # Get the character sheet
        sheet, _ = load_sheet(context, character=args.character)

        # Switch on the chosen subcommand
        if args.char_subcommand is None:
            # Return the character sheet
            logger.info('Reminding the user which character they are currently playing')
            await context.reply(f'You are playing {sheet.name} (lvl {sheet.level})')
        elif args.char_subcommand == "ability":
            ability_name = ' '.join(args.name)
            try:
                modifier = sheet.lookup_modifier(ability_name)
            except ValueError:
                logger.info(f'Modifier lookup failed for "{ability_name}"')
                await context.reply(f'Could not find a modifier for "{ability_name}"')
                return
            logger.info(f'Retrieved modifier for {ability_name} rolls: {modifier:+d}')
            await context.reply(f'{sheet.name}\'s modifier for {ability_name} is {modifier:+d}')
        elif args.char_subcommand == "list":
            state = ModronState.load()
            active = state.get_active_character(context.guild.id, context.author.id)[0]
            characters = list_available_characters(context.guild.id, context.author.id)
            await context.reply("Available characters: " + ", ".join(
                f"{name}" + (" (_active_)" if name == active else "") for name in characters
            ), delete_after=60)
        elif args.char_subcommand == "set":
            # First make sure it's an allowed character
            available = list_available_characters(context.guild.id, context.author.id)
            if args.choice not in available:
                await context.reply(f'{args.choice} is not within your list of characters: {", ".join(available)}',
                                    delete_after=120)
                return

            # Update the state
            state = ModronState.load()
            active = state.get_active_character(context.guild.id, context.author.id)
            state.characters[context.guild.id][context.author.id] = args.choice
            await context.reply(f'Set your active character to {args.choice} from {active}', delete_after=120)
            state.save()
        else:
            raise ValueError(f'Subcommand {args.char_subcommand} not yet implemented')


class HPTracker(InteractionModule):
    """Interaction for tracking character health"""

    def __init__(self):
        super(HPTracker, self).__init__(name='hp', description=_hp_description, help_string='Track character HP')

    def register_argparse(self, parser: ArgumentParser):
        parser.add_argument('--character', '-c', help='Name of character whose HP to change', default=None)

        # Add the "hp" command
        hp_subparsers = parser.add_subparsers(description='Available options for tracking HP', dest='hp_subcommand')

        heal_parser = hp_subparsers.add_parser('heal', help='Apply healing to a character')
        heal_parser.add_argument('amount', help='Amount of healing. Can be an integer or "full".')

        harm_parser = hp_subparsers.add_parser('harm', help='Apply damage to a character')
        harm_parser.add_argument('amount', help='Amount of damage. Must be an integer.', type=int)

        temp_parser = hp_subparsers.add_parser('temp', help='Grant temporary it points')
        temp_parser.add_argument('amount', help='Amount of change, or "reset" to change the temporary back to zero')

        max_parser = hp_subparsers.add_parser('max', help='Adjust hit point maximum')
        max_parser.add_argument('amount', help='Amount of change, or "reset" to change the temporary back to zero')

    async def interact(self, args: Namespace, context: Context):
        # Get the character sheet
        sheet, sheet_path = load_sheet(context, character=args.character)

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
                    raise ValueError(f'Could not parse amount: "{args.amount}"')

                change_msg = f"Healed {amount} hit points."
                sheet.heal(amount)
                logger.info(f'Healed {sheet.name} {amount} hit points')
        elif args.hp_subcommand == "harm":
            try:
                amount = int(args.amount)
            except ValueError:
                logger.info(f'Parse error for harm amount. Input: "{args.amount}"')
                raise ValueError(f'Could not parse amount: "{args.amount}"')

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
                    logger.info(f'Parse error for amount. Input: "{args.amount}"')
                    raise ValueError(f'Could not parse amount: "{args.amount}"')

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
                    logger.info(f'Parse error for amount. Input: "{args.amount}"')
                    raise ValueError(f'Could not parse amount: "{args.amount}"')

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

        await context.send(f'||{msg}||')
