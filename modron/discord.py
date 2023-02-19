"""Utility operations for discord"""
from typing import Optional, Tuple
from datetime import datetime
import logging

from discord import TextChannel, Message, Forbidden

from modron.utils import get_local_tz_offset

logger = logging.getLogger(__name__)


async def get_last_activity(channel: TextChannel) -> Optional[Tuple[datetime, Optional[Message]]]:
    """Get the last activity on a certain text channel

    Args:
        channel: Link to the channel
    Returns:
        - Time of the last message (if available)
        - The message object
    """

    try:
        message: Optional[Message] = None
        async for message in channel.history(limit=1, oldest_first=False):
            break
    except Forbidden:
        logger.warning(f'Bot lacks access to channel: {channel.name}')
        return datetime.fromtimestamp(0), None
    if message is not None:
        return timestamp_to_local_tz(message.created_at) + get_local_tz_offset(), message

    # Return a datetime of now for channels that have yet to be written in
    return datetime.fromtimestamp(0), None


def timestamp_to_local_tz(when: datetime) -> datetime:
    """Convert a time object from Discord (UTC) to an object in our local timezone

    Args:
        when: Timestamp from discord to be manipulated
    Returns:
        New timestamp, in our timezone without and
    """
    return when.replace(tzinfo=None) + get_local_tz_offset()
