"""Interaction for receiving a dice roll"""
import logging
from argparse import ArgumentParser, Namespace

import requests

from modron.dice import DiceRoll
from modron.interact import SlashCommandPayload
from modron.interact.base import InteractionModule
from modron.slack import BotClient

logger = logging.getLogger(__name__)


class DiceRollInteraction(InteractionModule):
    """Servicing requests to roll dice"""

    def __init__(self, client: BotClient):
        super().__init__(client, "roll", "Roll a set of dice")

    def register_argparse(self, parser: ArgumentParser):
        # Add the roll definition
        parser.add_argument("dice", help='List of dice to roll and a modifier. There should be no spaces in this'
                                         ' list of dice. Separate multiple types of dice with a plus sign.'
                                         ' For example, "1d6+4d6+4" would be accepted and "1d6+4d6 + 4"'
                                         ' would not.',
                            type=str)
        parser.add_argument("purpose", help='Purpose of the roll. Used for making the reply prettier.', nargs='?',
                            default=None, type=str)

        # Add modifiers to how the roll is computed
        adv_group = parser.add_mutually_exclusive_group(required=False)
        adv_group.add_argument("--advantage", "-a", help="Perform the roll at advantage", action='store_true')
        adv_group.add_argument("--disadvantage", "-d", help="Perform the roll at disadvantage", action='store_false')
        parser.add_argument("--reroll_ones", '-1', help="Re-roll any dice that roll a 1 the first time",
                            action='store_true')

    def interact(self, args: Namespace, payload: SlashCommandPayload):
        # Make the dice roll
        roll = DiceRoll.make_roll(args.dice, advantage=args.advantage, disadvantage=args.disadvantage,
                                  reroll_ones=args.reroll_ones)
        logger.info(f'{payload.user_id} requested to roll {roll}. Result = {roll.value}')

        # Make the reply
        if args.purpose is not None:
            reply = f'<@{payload.user_id}> rolled for {args.purpose}\n' \
                    f'{roll.roll_description} = _{roll.value}_\n' \
                    f'*Rolls*: {roll.dice}'
        else:
            reply = f'<@{payload.user_id}> rolled {roll.roll_description} = _{roll.value}_\n' \
                    f'*Rolls*: {roll.dice}'

        # POST the result back to the reply url
        requests.post(payload.response_url, json={
            'text': reply, 'mkdwn': True
        })
