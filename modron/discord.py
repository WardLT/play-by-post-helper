"""Utility operations for discord"""
from typing import List, Optional, Tuple
from datetime import datetime
import logging
import re

from discord import Guild, TextChannel, Message, Member, Forbidden

logger = logging.getLogger(__name__)


def match_channels_to_regex(guild: Guild, pattern: str) -> List[TextChannel]:
    """Find all channels that match a certain pattern

    Args:
        guild: Guild to evaluate
        pattern: Regular expression used to match channels
    """

    reg = re.compile(pattern)
    return [c for c in guild.channels if reg.match(c.name) and isinstance(c, TextChannel)]


async def get_last_activity(channel: TextChannel) -> Optional[Tuple[datetime, Optional[Member]]]:
    """Get the last activity on a certain text channel

    Args:
        channel: Link to the channel
    Returns:
        - Time of the last message (if available)
        - Whether the message was from the bot user
    """

    try:
        message: Message = await channel.history(limit=1, oldest_first=False).get()
    except Forbidden:
        logger.warning(f'Bot lacks access to channel: {channel.name}')
        # TODO (wardlt): Change to a timestamp of zero once we start using Discord
        return datetime.now(), None
    if message is not None:
        return message.created_at, message.author

    # Return a datetime of now for channels that have yet to be written in
    #  TODO (wardlt): Change this to a timestamp of zero once we start using Discord
    return datetime.now(), None
