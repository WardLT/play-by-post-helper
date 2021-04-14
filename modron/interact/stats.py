"""Statistics about play. E.g., dice rolls"""
import json
import logging
from argparse import ArgumentParser, Namespace

import pandas as pd

from modron import SlashCommandPayload, get_config
from modron.dice import DiceRoll
from modron.dice.stats import DiceRollStatistics
from modron.interact.base import InteractionModule

_description = """Access statistics about play.

A present, provides commands to returns how "fair" dice have been.
"""

logger = logging.getLogger(__name__)
config = get_config()


class StatisticModule(InteractionModule):
    """Module for returning statistics about play"""

    def __init__(self, clients):
        super().__init__(
            clients=clients,
            name='stats',
            help_string='Get statistics about play',
            description=_description
        )

    def register_argparse(self, parser: ArgumentParser):
        # Add in a dice statistics command
        parser.add_argument("--all-players", action='store_true', help="Get actions from all players")
        parser.add_argument("--character", "-c", type=str, default=None, help="Name of the character to query")
        parser.add_argument("--reason", type=str, default=None, help="Purpose of the roll (e.g., perception)")
        parser.add_argument("--die", type=str, default="d20", help="Type of the dice")
        parser.add_argument("--channel", type=str, help="Which channel(s) to draw from. Can be a regex")
        parser.add_argument("--no-modifiers", action='store_true',
                            help="Only get dice performed without any modification")

    def interact(self, args: Namespace, payload: SlashCommandPayload):
        # Load in the dice rolls from the appropriate team
        dice_path = config.get_dice_log_path(payload.team_id)
        dice_log = pd.read_csv(dice_path)
        logger.info(f'Loaded {len(dice_log)} records from {dice_path}')

        # Determine the desired dice
        user_input = args.die.lower()
        try:
            if user_input.startswith('d'):
                die_choice = int(user_input[1:])
            else:
                die_choice = int(user_input)
        except ValueError:
            raise ValueError(f'Bad dice value: {args.die}')

        # Screen down to the desired dice rolls
        if args.character is None:
            user_name = self.clients[payload.team_id].get_user_name(payload.user_id)
        else:
            user_name = args.character

        if not args.all_players and len(dice_log) > 0:
            dice_log.query(f'user=="{user_name}"', inplace=True)
            logger.info(f'Reduced to {len(dice_log)} records from {user_name}')

        if len(dice_log) > 0:
            dice_log['dice_faces'] = dice_log['dice'].apply(lambda x: DiceRoll.make_roll(x).dice)
            dice_log = dice_log[dice_log['dice_faces'].apply(lambda x: die_choice in x)]
            logger.info(f'Reduced to {len(dice_log)} records that rolled a d{die_choice}')

        if args.reason is not None and len(dice_log) > 0:
            dice_log.query(f'reason=="{args.reason}"', inplace=True)
            logger.info(f'Reduced to {len(dice_log)} records with purpose "{args.reason}"')

        if args.no_modifiers and len(dice_log) > 0:
            dice_log.query('not (advantage or disadvantage or reroll_ones)', inplace=True)
            logger.info(f'Reduced to {len(dice_log)} records without any modifiers')

        if args.channel and len(dice_log) > 0:
            dice_log = dice_log[dice_log['channel'].str.contains(args.channel)]
            match_channels = dice_log['channel'].value_counts().index.tolist()
            logger.info(f'Downselected to channels that match "{args.channel}"')
        else:
            match_channels = None

        # If necessary, match dice rolls
        if len(dice_log) == 0:
            payload.send_reply('No matching dice rolls.', ephemeral=True)
            return

        # Extract the values of interest
        dice_log = dice_log.copy()  # Avoid copy warnings
        dice_log["dice_values"] = dice_log["dice_values"].apply(json.loads)
        rolls = []
        for _, row in dice_log.iterrows():
            rolls.extend([v for f, v in zip(row["dice_faces"], row["dice_values"]) if f == die_choice])
        logger.info(f'Extracted {len(rolls)} rolls to evaluate')

        # Compute statistics
        summary = DiceRollStatistics.from_rolls(die_choice, rolls)

        # Generate the output
        header = f'Pulled {len(rolls)} d{die_choice} rolls'
        if args.reason is not None:
            header += f' for {args.reason}'
        header += ' from all players' if args.all_players else f' from {user_name}'
        if match_channels is not None:
            header += f' in channels: {", ".join(match_channels)}'

        #   Special case: Only the output
        if len(rolls) == 0:
            payload.send_reply(header, ephemeral=True)
            return

        output = [header, f'*Last {min(5, len(rolls))} rolls*: {", ".join(map(str, rolls[-5:]))}']
        if args.reason is None:
            common_rolls = dice_log[~dice_log['reason'].isnull()].reason.value_counts()
            output.append(f'*Most common rolls*: {", ".join(common_rolls.iloc[:3].index)}')

        output.append(f'*Die description*: {summary.models[0].description}')

        # Send outputs to user
        payload.send_reply("\n".join(output), ephemeral=True)
