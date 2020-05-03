"""NPC generator for the DM"""
import logging
from argparse import ArgumentParser, Namespace

import requests

from modron.interact import InteractionModule, SlashCommandPayload
from modron.npc import generate_npc
from modron.slack import BotClient
from modron import config

_description = '''Generate a randomized NPC

Follows the method used by MAB to create NPCs for Kaluth'''

logger = logging.getLogger(__name__)


def generate_and_render_npcs(location: str, n: int) -> dict:
    """Generate a specified number of NPCs and render them
    as a Slack Message payload

    Args:
        location (str): Name of the demographic template to use
        n (int): Number of NPCs to create
    Returns:
        (dict): Slack-format message payload
    """
    npcs = [generate_npc(location) for _ in range(n)]

    # Make each NPC a separate box
    blocks = [{
        'type': 'section',
        'text': {
            'type': 'mrkdwn',
            'text': f'{n} NPCs from {location}'
        }
    }]
    for npc in npcs:
        # Put in a divider
        blocks.append({'type': 'divider'})

        # Assemble the NPC info
        fields = []
        for k, v in npc.items():
            fields.append({
                'type': 'mrkdwn',
                'text': f'*{k}*: {v}'
            })
        blocks.append({
            'type': 'section',
            'fields': fields
        })

    return {"blocks": blocks}


class NPCGenerator(InteractionModule):
    """Module for generating randomized NPCs"""

    def __init__(self, client: BotClient):
        super().__init__(
            client=client,
            name='npcgen',
            help_string='Generate a new NPC',
            description=_description
        )

    def register_argparse(self, parser: ArgumentParser):
        parser.add_argument('n', help='Number of NPCs to generate', type=int, default=1)
        parser.add_argument('--location', '-l', help='Which demographic template to use',
                            default='default', choices=config.RACE_DISTRIBUTION.keys(), type=str)

    def interact(self, args: Namespace, payload: SlashCommandPayload):
        # Log the interaction
        logger.info(f'{payload.user_id} requested to make {args.n} NPCs from {args.location}')

        # Make the NPCs and send them back
        reply_content = generate_and_render_npcs(args.location, args.n)
        requests.post(payload.response_url, json=reply_content)
