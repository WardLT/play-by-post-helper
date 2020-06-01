"""NPC generator for the DM"""
import logging
from tempfile import TemporaryDirectory
from argparse import ArgumentParser, Namespace
from string import Template
import os

from tabulate import tabulate
import pdfkit

from modron.interact import InteractionModule, SlashCommandPayload
from modron.npc import generate_npc
from modron.config import get_config

config = get_config()

_description = '''Generate a randomized NPC

Follows the method used by MAB to create NPCs for Kaluth'''

logger = logging.getLogger(__name__)


_table_template = '''<!doctype html>
<html>
<head>
<!-- Latest compiled and minified CSS -->
<link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/3.4.1/css/bootstrap.min.css"
 integrity="sha384-HSMxcRTRxnN+Bdg0JdbxYKrThecOKuH5zCYotlSAcp1+c8xmyTe9GYg1l9a69psu" crossorigin="anonymous">

<!-- Optional theme -->
<link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/3.4.1/css/bootstrap-theme.min.css"
 integrity="sha384-6pzBo3FDv/PJ8r2KRkGHifhEocL+1X2rVCTTkUfGk7/0pbek5mMa1upzvWbrUbOZ" crossorigin="anonymous">

<!-- Latest compiled and minified JavaScript -->
<script src="https://stackpath.bootstrapcdn.com/bootstrap/3.4.1/js/bootstrap.min.js"
 integrity="sha384-aJ21OjlMXNL5UyIl/XNwTMqvzeRMZH2w8c5cRVpzpU8Y5bApTppSuUkhZXN0VxHd" crossorigin="anonymous"></script>

<title>$title</title>

</head>
<body>
$content
</body>
</html>'''


def generate_and_render_npcs(location: str, n: int) -> str:
    """Generate a specified number of NPCs and render them
    as an HTML table

    Args:
        location (str): Name of the demographic template to use
        n (int): Number of NPCs to create
    Returns:
        (str) HTML document to upload
    """
    assert n > 0, "You must make at least one NPC"
    npcs = [generate_npc(location) for _ in range(n)]

    # Render an HTML table
    headers = list(npcs[0].keys())
    table = [[x[k] for k in headers] for x in npcs]
    table_content = tabulate(table, headers, tablefmt='html')

    # Add in the style header
    table_content = table_content.replace("<table>", "<table class=\"table table-striped\">")

    return Template(_table_template).substitute(title=f'{n} NPCs from {location}',
                                                content=table_content)


class NPCGenerator(InteractionModule):
    """Module for generating randomized NPCs"""

    def __init__(self, clients):
        super().__init__(
            clients=clients,
            name='npcgen',
            help_string='Generate a new NPC',
            description=_description
        )

    def register_argparse(self, parser: ArgumentParser):
        parser.add_argument('n', help='Number of NPCs to generate', type=int, default=1)
        parser.add_argument('--location', '-l', help='Which demographic template to use',
                            default='default', choices=config.npc_race_dist.keys(), type=str)

    def interact(self, args: Namespace, payload: SlashCommandPayload):
        # Log the interaction
        logger.info(f'{payload.user_id} requested to make {args.n} NPCs from {args.location}')

        # Make the HTML table
        npc_table = generate_and_render_npcs(args.location, args.n)

        # Check if the command was invoked in a channel. If not, we must send file as a DM
        if not self.clients[payload.team_id].conversation_is_channel(payload.channel_id):
            logger.info('Command came from a private channel, will send it to them directly')
            result = self.clients[payload.team_id].conversations_open(users=payload.user_id)
            channel_id = result['channel']['id']
        else:
            channel_id = payload.channel_id

        with TemporaryDirectory() as td:
            # Convert the table to PDF
            pdf_path = os.path.join(td, f'npcs_{args.n}_{args.location}.pdf')
            pdfkit.from_string(npc_table, pdf_path, options={
                'orientation': 'landscape',
                'page-size': 'Letter'
            })

            # Upload it as a file
            self.clients[payload.team_id].files_upload(
                channels=channel_id, title=f'{args.n} NPCs from {args.location}',
                file=pdf_path, initial_comment=f'The {args.n} NPCs you requested')
