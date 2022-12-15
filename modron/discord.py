"""Utility operations for discord"""
from typing import Optional, Tuple
from datetime import datetime
import logging

from discord import TextChannel, Message, Member, Forbidden

from modron.utils import get_local_tz_offset

logger = logging.getLogger(__name__)


async def get_last_activity(channel: TextChannel) -> Optional[Tuple[datetime, Optional[Member]]]:
    """Get the last activity on a certain text channel

    Args:
        channel: Link to the channel
    Returns:
        - Time of the last message (if available)
        - Whether the message was from the bot user
    """

    try:
        message: Optional[Message] = None
        async for message in channel.history(limit=1, oldest_first=False):
            break
    except Forbidden:
        logger.warning(f'Bot lacks access to channel: {channel.name}')
        return datetime.fromtimestamp(0), None
    if message is not None:
        return message.created_at.replace(tzinfo=None) + get_local_tz_offset(), message.author

    # Return a datetime of now for channels that have yet to be written in
    return datetime.fromtimestamp(0), None
