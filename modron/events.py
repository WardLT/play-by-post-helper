"""Functions used to respond to events"""
import logging
import platform
from datetime import datetime

import humanize

from modron.slack import BotClient

logger = logging.getLogger(__name__)


def status_check(event, client: BotClient, start_time: datetime = datetime.now()):
    """Reply to a message event with a status check

    Args:
        event (dict): Event data
        client (BotClient): Client to use when replying
        start_time (datetime): Date this server was started
    """
    # Figure out where this came from
    reply_channel = event["event"]["channel"]
    sender = event["event"]["user"]
    if sender == client.my_id:
        logger.info("The message is me. Not going to talk to myself!")
        return

    # Reply back with something
    logger.info(f'Received a direct message from {sender}')
    client.chat_postMessage(
        channel=reply_channel,
        text=f'Hello! I\'ve been awake {humanize.naturaldelta(datetime.now() - start_time)}'
             f' on {platform.node()}'
    )