"""Interaction for receiving a dice roll"""
import logging
from argparse import ArgumentParser, Namespace
from typing import List

import requests

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
    for v, d in zip(roll.results, roll.dice):
        if v == 1:
            output.append(f'*1*')
        elif v == d:
            output.append(f'_{v}_')
        else:
            output.append(str(v))
    return output


_description = """Roll a set of dice.

This module lets you roll any kind of die and 
supports all of the dice rules of D&D 5e,
such as re-rolling 1s and rolling at advantage.

The dice notation follows common conventions,
where dice are expressed in the format:

`<number of dice>d<number of sides>[+|-]<modifier>`

## examples

A common dice roll without any special rolls: `/modron roll 1d20+1`

A common dice roll, with a defined purpose: `/modron roll 10d6+5 sneak attack damage`

Option flags before the dice descriptions change how the rolls are made.
For example, the `-d` or `--disadvantage` flags signal for Modron to roll
at disadvantage:

`/roll -d 1d20+2`
"""


class DiceRollInteraction(InteractionModule):
    """Servicing requests to roll dice"""

    def __init__(self, client: BotClient):
        super().__init__(client, "roll", "Roll a set of dice", _description)

    def register_argparse(self, parser: ArgumentParser):
        # Add the roll definition
        parser.add_argument("dice", help='List of dice to roll and a modifier. There should be no spaces in this'
                                         ' list of dice. Separate multiple types of dice with a plus sign.'
                                         ' For example, "1d6+4d6+4" would be accepted and "1d6+4d6 + 4"'
                                         ' would not.',
                            type=str)
        parser.add_argument("purpose", help='Purpose of the roll. Used for making the reply prettier.',
                            nargs='*', default=None, type=str)

        # Add modifiers to how the roll is computed
        adv_group = parser.add_mutually_exclusive_group(required=False)
        adv_group.add_argument("--advantage", "-a", help="Perform the roll at advantage", action='store_true')
        adv_group.add_argument("--disadvantage", "-d", help="Perform the roll at disadvantage", action='store_true')
        parser.add_argument("--reroll_ones", '-1', help="Re-roll any dice that roll a 1 the first time",
                            action='store_true')

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
        reply += f'\n*Rolls*: {" ".join(_render_dice_rolls(roll))}'

        # POST the result back to the reply url
        requests.post(payload.response_url, json={
            'text': reply, 'mkdwn': True,
            'response_type': 'in_channel',
        })
