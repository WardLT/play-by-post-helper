"""Functions used to respond to events"""
import logging
import platform
from datetime import datetime
from typing import Dict

import humanize

from modron.slack import BotClient

logger = logging.getLogger(__name__)


def status_check(event, clients: Dict[str, BotClient], start_time: datetime = datetime.now()):
    """Reply to a message event with a status check

    Args:
        event (dict): Event data
        clients: Client to use when replying, key is the team ID
        start_time (datetime): Date this server was started
    """

    # Determine the team and get the appropriate client
    team_id = event["team_id"]
    client = clients[team_id]
    logger.info(f'Received a status check event from {team_id}')

    # Figure out where this came from
    reply_channel = event["event"]["channel"]
    sender = event["event"].get("user_id")
    if sender == client.my_id or sender is None:
        logger.info("The message is me. Not going to talk to myself!")
        return

    # Reply back with something
    logger.info(f'Received a direct message from {sender}')
    client.chat_postMessage(
        channel=reply_channel,
        text=f'Hello! I\'ve been awake {humanize.naturaldelta(datetime.now() - start_time)}'
             f' on {platform.node()}'
    )
