"""Interaction for receiving a dice roll"""
import csv
import json
import logging
import os
from argparse import ArgumentParser, Namespace
from datetime import datetime
from typing import List, NoReturn

import requests

from modron.characters import list_available_characters, load_character
from modron.config import get_config
from modron.dice import DiceRoll, dice_regex
from modron.interact import SlashCommandPayload
from modron.interact.base import InteractionModule

logger = logging.getLogger(__name__)
config = get_config()


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
            ' '.join([value_str if u else f'~{v}~' for v, u in zip(rolls, was_used)])
        )
    return output


_description = """Roll dice with all the options of D&D 5e.

Dice are expressed in the format: `<number of dice>d<number of sides>[+|-]<modifier>`

*examples*

A common dice roll without any special rolls: `/modron roll 1d20+1`
A common dice roll, with a defined purpose: `/modron roll 10d6+5 sneak attack damage`

Option flags alter rules when rolling. Example: rolling at disadvantage: `/roll -d 1d20+2`

If you have a character sheet registered, (call `/modron character` to find out) you can
instead list the name of the ability you wish to roll. For example, `/roll str save` to
roll a strength save.

Call `/modron roll --help` for full details
"""


class DiceRollInteraction(InteractionModule):
    """Servicing requests to roll dice"""

    def __init__(self, clients):
        super().__init__(clients, "roll", "Roll a set of dice. Ex: `/modron roll 1d20+4 --advantage`", _description)

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

        # Add modifiers to how the roll is computed
        adv_group = parser.add_mutually_exclusive_group(required=False)
        adv_group.add_argument("--advantage", "-a", help="Perform the roll at advantage", action='store_true')
        adv_group.add_argument("--disadvantage", "-d", help="Perform the roll at disadvantage", action='store_true')
        parser.add_argument("--reroll_ones", '-1', help="Re-roll any dice that roll a 1 the first time",
                            action='store_true')

    def log_dice_roll(self, payload: SlashCommandPayload, roll: DiceRoll, purpose: str) -> NoReturn:
        """Log a dice roll to disk

        Only logs dice rolls if ``config.DICE_LOG`` is not ``None``
        and the requests comes from a channel that is not on the skip list.

        Args:
            payload (SlashCommandPayload): Command send to Modron
            roll (DiceRoll): Value of the dice roll
            purpose (str): Purpose of the roll
        """

        # Determine if we should log or not
        if payload.channel_id.startswith('C'):
            channel_name = self.clients[payload.team_id].get_channel_name(payload.channel_id)
            skipped_channel = channel_name in config.team_options[payload.team_id].dice_skip_channels
            private_channel = False
        else:
            skipped_channel = False
            private_channel = True
            channel_name = None
        no_log = not config.team_options[payload.team_id].dice_log

        if no_log or skipped_channel or private_channel:
            logger.info(f'Refusing to log dice roll. Reasons: No log - {no_log}, skipped channel - {skipped_channel},'
                        f' private channel - {private_channel}')
            return

        # Get the information about this dice roll
        dice_info = {
            'time': datetime.now().isoformat(),
            'user': self.clients[payload.team_id].get_user_name(payload.user_id),
            'channel': channel_name,
            'reason': purpose,
            'dice': roll.dice_description,
            'advantage': roll.advantage,
            'disadvantage': roll.disadvantage,
            'reroll_ones': roll.reroll_ones,
            'total_value': roll.value,
            'dice_values': json.dumps(roll.dice_values)
        }

        # If desired, save the dice roll
        dice_path = config.get_dice_log_path(payload.team_id)
        new_file = not os.path.isfile(dice_path)
        os.makedirs(os.path.dirname(dice_path), exist_ok=True)
        with open(config.get_dice_log_path(payload.team_id), 'a') as fp:
            writer = csv.DictWriter(fp, fieldnames=dice_info.keys())
            if new_file:
                writer.writeheader()
            writer.writerow(dice_info)

    def interact(self, args: Namespace, payload: SlashCommandPayload):
        # Check if the user is requesting a roll by name
        if dice_regex.match(args.dice) is None:
            logger.info('Dice did not match regex, attempting to match to character ability')
            available_chars = list_available_characters(payload.team_id, payload.user_id)
            if len(available_chars) == 0:
                logging.info(f'Seems like user {payload.user_id} needs to register a character')
                payload.send_reply(
                    f'Did you mean to request a character roll? {args.dice} does not seem like a dice roll, '
                    f'but you have not registered a character yet. Talk to Logan about registering your sheet.'
                )
                return
            elif len(available_chars) == 1:
                # Reformat command to use a specific character roll
                sheet = load_character(payload.team_id, available_chars[0])
                ability_name = ' '.join([args.dice] + args.purpose)

                # Lookup the ability
                modifier = sheet.lookup_modifier(ability_name)
                args.dice = f'1d20{modifier:+d}'
                args.purpose = [ability_name]
                logger.info(f'Reformatted command to be for {ability_name} for {sheet.name}')
            else:
                raise ValueError('Multi-character support is not yet implemented')

        # Make the dice roll
        roll = DiceRoll.make_roll(args.dice, advantage=args.advantage, disadvantage=args.disadvantage,
                                  reroll_ones=args.reroll_ones)

        # Make the reply
        purpose = ' '.join(args.purpose)
        if len(purpose) > 0:
            reply = f'<@{payload.user_id}> rolled for {purpose}\n' \
                    f'{roll.roll_description} = *{roll.value}*'
            logger.info(f'{payload.user_id} requested to roll {roll.roll_description} for {purpose}.'
                        f' Result = {roll.value}')
        else:
            reply = f'<@{payload.user_id}> rolled {roll.roll_description} = *{roll.value}*'
            logger.info(f'{payload.user_id} requested to roll {roll.roll_description}.'
                        f' Result = {roll.value}')
        reply += f'\nRolls: {", ".join(_render_dice_rolls(roll))}'

        # POST the result back to the reply url
        requests.post(payload.response_url, json={
            'text': reply, 'mkdwn': True,
            'response_type': 'in_channel',
        })

        # Log the dice roll
        self.log_dice_roll(payload, roll, purpose)
