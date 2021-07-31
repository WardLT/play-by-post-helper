"""Utility operations for discord"""
from typing import List, Optional, Tuple
from datetime import datetime
import logging
import re

from discord import Guild, TextChannel, Message, Member, Client


logger = logging.getLogger(__name__)


class ModronClient(Client):
    """Client used to connect to Discord"""

    async def on_ready(self):
        logger.info(f'Logged on as {self.user}')

    async def on_disconnect(self):
        logger.warning('Disconnected from Discord service')

    async def on_connect(self):
        logger.info('Connected to Discord service')


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

    message: Message = await channel.history(limit=1, oldest_first=False).get()
    if message is not None:
        return message.created_at, message.author

    # Return a datetime of now for channels that have yet to be written in
    #  TODO (wardlt): Change this to a timestamp of zero once we start using Discord
    return datetime.now(), None
