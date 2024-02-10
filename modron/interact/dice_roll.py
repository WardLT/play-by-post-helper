"""Interaction for receiving a dice roll"""
import csv
import json
import logging
import os
import re
from argparse import ArgumentParser, Namespace
from datetime import datetime
from typing import List, Optional

from discord import TextChannel, Guild
from discord.ext.commands import Context
from discord import utils

from modron.config import config
from modron.db import ModronState
from modron.dice import DiceRoll, dice_regex
from modron.interact.base import InteractionModule
from modron.characters import load_character, list_available_characters

logger = logging.getLogger(__name__)

_private_channel_pattern = re.compile(r'(?:[-_]|^)gm(?:[-_]|$)')


def _render_dice_rolls(roll: DiceRoll) -> List[str]:
    """Render the dice values in an pretty HTML format

    Args:
        roll (DiceRoll): Dice roll to be rendered
    Returns:
        ([str]) Rendered form of each dice
    """

    output = []
    for (value, rolls), d in zip(roll.results, roll.dice):
        # Get whether the dice was used
        used_ix = rolls.index(value)
        assert used_ix is not None, "Outcome of roll is not in the list of dice rolled!?"
        was_used = [False] * len(rolls)
        was_used[used_ix] = True

        # Render the roll value
        if value == 1:
            value_str = '*1*'
        elif value == d:
            value_str = f'_{value}_'
        else:
            value_str = f'{value}'

        # Render the value of all dice
        output.append(
            ' '.join([value_str if u else f'~~{v}~~' for v, u in zip(rolls, was_used)])
        )
    return output


_description = """Roll dice with all the options of D&D 5e.

Dice are expressed in the format: `<number of dice>d<number of sides>[+|-]<modifier>`

Dice results will be sent to the public roll channel for public in-character channels,
a GM-only channel if the roll is blind,
and to the channel in which you made the roll otherwise.

*examples*

A common dice roll without any special rolls: `$modron roll 1d20+1`
A common dice roll, with a defined purpose: `$modron roll 10d6+5 sneak attack damage`

Option flags alter rules when rolling. Example: rolling at disadvantage: `$roll -d 1d20+2`
"""


class DiceRollInteraction(InteractionModule):
    """Servicing requests to roll dice"""

    def __init__(self):
        super().__init__("roll", "Roll a set of dice. Ex: `/modron roll 1d20+4 --advantage`", _description)

    def register_argparse(self, parser: ArgumentParser):
        # Add the roll definition
        parser.add_argument("dice", help='List of dice to roll and a modifier. There should be no spaces in this'
                                         ' list of dice. Separate multiple types of dice with a plus sign.'
                                         ' For example, "1d6+4d6+4" would be accepted and "1d6+4d6 + 4"'
                                         ' would not.\n'
                                         'Alternatively, you can omit the dice and instead have Modron lookup '
                                         'your roll modifier based on the purpose (e.g., "stealth")',
                            type=str)
        parser.add_argument("purpose", help='Purpose of the roll. Used for making the reply prettier '
                                            'and tracking player statistics.',
                            nargs='*', default=None, type=str)
        parser.add_argument("--character", "-c", help='Name of the character sheet to use')

        # Add modifiers to how the roll is computed
        adv_group = parser.add_mutually_exclusive_group(required=False)
        adv_group.add_argument("--advantage", "-a", help="Perform the roll at advantage", action='store_true')
        adv_group.add_argument("--disadvantage", "-d", help="Perform the roll at disadvantage", action='store_true')
        reroll_group = parser.add_mutually_exclusive_group(required=False)
        reroll_group.add_argument("--reroll_ones", '-1', help="Re-roll any dice that roll a 1 the first time",
                                  action='store_true')
        reroll_group.add_argument("--reroll_twos", '-2', help="Re-roll any dice that roll a 1 or 2 the first time",
                                  action='store_true')

        # Mark how it is logged
        blind_group = parser.add_mutually_exclusive_group(required=False)
        blind_group.add_argument('--blind', '-b', help='Only report the roll to the GM, regardless of the defaults',
                                 action='store_const', const=True)
        blind_group.add_argument('--show', '-s', help='Report the roll to this channel, regardless of the defaults',
                                 action='store_const', const=True)

    def log_dice_roll(self, context: Context, character: Optional[str], roll: DiceRoll, purpose: str):
        """Log a dice roll to disk

        Only logs dice rolls if ``config.DICE_LOG`` is not ``None``
        and the requests comes from a channel that is not on the skip list.

        Args:
            context: Command send to Modron
            character:
            roll: Value of the dice roll
            purpose: Purpose of the roll
        """

        # Get the channels where tracking is allowed
        guild: Guild = context.guild
        allowed_channels = sum([
            cat.channels for cat in guild.categories if cat.id in config.team_options[guild.id].dice_tracked_categories
        ], [])

        # Determine if we should log or not
        if isinstance(context.channel, TextChannel):
            channel: TextChannel = context.channel
            channel_name = channel.name
            skipped_channel = channel not in allowed_channels
        else:
            skipped_channel = False
            channel_name = None
        no_log = not config.team_options[context.guild.id].dice_log

        if no_log or skipped_channel:
            logger.info(f'Refusing to log dice roll. Reasons: No log - {no_log}, skipped channel - {skipped_channel}')
            return

        # Get the information about this dice roll
        dice_info = {
            'time': datetime.now().isoformat(),
            'user': context.author.name,
            'user_id': context.author.id,
            'character': character,
            'channel': channel_name,
            'reason': purpose,
            'dice': roll.dice_description,
            'advantage': roll.advantage,
            'disadvantage': roll.disadvantage,
            'reroll_ones': roll.reroll_ones,
            'reroll_twos': roll.reroll_twos,
            'total_value': roll.value,
            'dice_values': json.dumps(roll.dice_values),
            'raw_rolls': json.dumps(roll.raw_rolls)
        }

        # If desired, save the dice roll
        dice_path = config.get_dice_log_path(context.guild.id)
        new_file = not os.path.isfile(dice_path)
        os.makedirs(os.path.dirname(dice_path), exist_ok=True)
        with open(config.get_dice_log_path(context.guild.id), 'a') as fp:
            writer = csv.DictWriter(fp, fieldnames=list(dice_info.keys()))
            if new_file:
                writer.writeheader()
            writer.writerow(dice_info)

    async def interact(self, args: Namespace, context: Context):
        # Get the associated character
        if args.character is None:
            if len(list_available_characters(context.guild.id, context.author.id)) == 0:
                character = None
            else:
                state = ModronState.load()
                character = state.get_active_character(context.guild.id, context.author.id)[0]
        else:
            character = args.character.lower()

        # Check if the user is requesting a roll by name
        if args.dice.lower() == 'luck':
            args.dice = '1d20'
            args.purpose = ['luck']
        elif dice_regex.match(args.dice) is None:
            logger.info('Dice did not match regex, attempting to match to character ability')
            if character is None:
                raise ValueError('No characters available for your player')

            # Reformat command to use a specific character roll
            sheet, _ = load_character(context.guild.id, character)
            ability_name = ' '.join([args.dice] + args.purpose)

            # Lookup the ability
            modifier = sheet.lookup_modifier(ability_name)
            args.dice = f'1d20{modifier:+d}'
            args.purpose = [ability_name]
            logger.info(f'Reformatted command to be for {ability_name} for {sheet.name}')

        # Make the dice roll
        roll = DiceRoll.make_roll(args.dice, advantage=args.advantage, disadvantage=args.disadvantage,
                                  reroll_ones=args.reroll_ones, reroll_twos=args.reroll_twos)

        # Make the reply
        purpose = ' '.join(args.purpose)
        if len(purpose) > 0:
            reply = f'<@!{context.author.id}> rolled for {purpose}\n' \
                    f'{roll.roll_description} = *{roll.value}*'
            logger.info(f'{context.author.name} requested to roll {roll.roll_description} for {purpose}.'
                        f' Result = {roll.value}')
        else:
            reply = f'<@!{context.author.id}> rolled {roll.roll_description} = *{roll.value}*'
            logger.info(f'{context.author.name} requested to roll {roll.roll_description}.'
                        f' Result = {roll.value}')
        reply += f'\nRolls: {", ".join(_render_dice_rolls(roll))}'

        # Conditions which define where the dice roll is going
        blind_channel = ' '.join(args.purpose).lower() in config.team_options[context.guild.id].blind_rolls
        force_blind = args.blind
        force_show = args.show
        ic_channel = context.channel.name in config.team_options[context.guild.id].watch_channels
        is_private = _private_channel_pattern.search(context.channel.name) is not None
        has_public_channel = config.team_options[context.guild.id].public_channel is not None

        # Send the result appropriate
        if force_blind or (blind_channel and not force_show):  # Role blind
            channel_name = config.team_options[context.guild.id].blind_channel
            channel: TextChannel = utils.get(context.guild.channels, name=channel_name)

            # Tell the user we are rolling blind
            await context.send(f'<@!{context.author.id}> rolled {roll.roll_description}, and '
                               'only the GM will see the result')
            await channel.send(reply)
        elif (ic_channel and is_private) or not ic_channel or not has_public_channel:
            # Reply in channel
            await context.send(reply)
        else:  # Public channel exists, we're in an IC channel and that channel is not private
            # Reply in the public dice roll
            channel_name = config.team_options[context.guild.id].public_channel
            channel: TextChannel = utils.get(context.guild.channels, name=channel_name)
            await channel.send(reply)

        # Log the dice roll
        self.log_dice_roll(context, character, roll, purpose)
