"""Test utility functions"""

from datetime import datetime

from discord import Guild, utils, TextChannel
from pytest import mark

from modron.discord import get_last_activity
from modron.db import LastMessage


@mark.asyncio
async def test_last_activity(guild: Guild):
    """Make sure the last activity works as desired"""

    # Send a message in bot testing
    channel: TextChannel = utils.get(guild.channels, name='bot_testing')
    msg = await channel.send('Test message')
    try:
        time, last_msg = await get_last_activity(channel)
        assert abs((datetime.now() - time).total_seconds()) < 30
    finally:
        await msg.delete()

    # Make a record about the last message
    record = LastMessage.from_discord(msg)
    assert abs((datetime.now() - record.last_time).total_seconds()) < 30
