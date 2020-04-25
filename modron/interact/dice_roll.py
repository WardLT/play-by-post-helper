"""Interaction for receiving a dice roll"""
import csv
import json
import logging
import os
from argparse import ArgumentParser, Namespace
from datetime import datetime
from typing import List, NoReturn

import requests

from modron import config
from modron.dice import DiceRoll
from modron.interact import SlashCommandPayload
from modron.interact.base import InteractionModule
from modron.slack import BotClient

logger = logging.getLogger(__name__)


def _render_dice_rolls(roll: DiceRoll) -> List[str]:
    """Render the dice values in an pretty HTML format

    Args:
        roll (DiceRoll): Dice roll to be rendered
    Returns:
        ([str]) Rendered form of each dice
    """

    output = []
    for (value, unused), d in zip(roll.results, roll.dice):
        # Display the unused results
        if len(unused) == 0:
            u = ''
        else:
            u = ' '.join([f'~{x}~' for x in unused]) + ' '

        if value == 1:
            output.append(f'{u}*1*')
        elif value == d:
            output.append(f'{u}_{value}_')
        else:
            output.append(f'{u}{value}')
    return output


_description = """Roll dice with all the options of D&D 5e.

Dice are expressed in the format: `<number of dice>d<number of sides>[+|-]<modifier>`

*examples*

A common dice roll without any special rolls: `/modron roll 1d20+1`
A common dice roll, with a defined purpose: `/modron roll 10d6+5 sneak attack damage`

Option flags alter rules when rolling. Example: rolling at disadvantage: `/roll -d 1d20+2`

Call `/modron roll --help` for full details
"""


class DiceRollInteraction(InteractionModule):
    """Servicing requests to roll dice"""

    def __init__(self, client: BotClient):
        super().__init__(client, "roll", "Roll a set of dice. Ex: `/modron roll 1d20+4 --advantage`", _description)

    def register_argparse(self, parser: ArgumentParser):
        # Add the roll definition
        parser.add_argument("dice", help='List of dice to roll and a modifier. There should be no spaces in this'
                                         ' list of dice. Separate multiple types of dice with a plus sign.'
                                         ' For example, "1d6+4d6+4" would be accepted and "1d6+4d6 + 4"'
                                         ' would not.',
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
        channel_name = self.client.get_channel_name(payload.channel_id)
        if config.DICE_LOG is None or channel_name in config.DICE_SKIP_CHANNELS\
                or not self.client.conversation_is_public_channel(payload.channel_id):
            logger.debug('Refusing to log dice roll')
            return

        # Get the information about this dice roll
        dice_info = {
            'time': datetime.now().isoformat(),
            'user': self.client.get_user_name(payload.user_id),
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
        new_file = not os.path.isfile(config.DICE_LOG)
        with open(config.DICE_LOG, 'w') as fp:
            writer = csv.DictWriter(fp, fieldnames=dice_info.keys())
            if new_file:
                writer.writeheader()
            writer.writerow(dice_info)

    def interact(self, args: Namespace, payload: SlashCommandPayload):
        # Make the dice roll
        roll = DiceRoll.make_roll(args.dice, advantage=args.advantage, disadvantage=args.disadvantage,
                                  reroll_ones=args.reroll_ones)

        # Make the reply
        purpose = ' '.join(args.purpose)
        if len(purpose) > 0:
            reply = f'<@{payload.user_id}> rolled for {purpose}\n' \
                    f'{roll.roll_description} = _{roll.value}_'
            logger.info(f'{payload.user_id} requested to roll {roll.roll_description} for {purpose}.'
                        f' Result = {roll.value}')
        else:
            reply = f'<@{payload.user_id}> rolled {roll.roll_description} = _{roll.value}_'
            logger.info(f'{payload.user_id} requested to roll {roll.roll_description}.'
                        f' Result = {roll.value}')
        reply += f'\n*Rolls*: {", ".join(_render_dice_rolls(roll))}'

        # POST the result back to the reply url
        requests.post(payload.response_url, json={
            'text': reply, 'mkdwn': True,
            'response_type': 'in_channel',
        })

        # Log the dice roll
        self.log_dice_roll(payload, roll, purpose)
