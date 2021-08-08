"""Tests related to the Slack API"""
from discord import Guild

from modron.discord import match_channels_to_regex
from modron.bot import ModronClient


def test_channel_match(client: ModronClient, guild: Guild):
    assert client.is_ready()
    matched = match_channels_to_regex(guild, '^ic_all$')
    assert [m.name for m in matched] == ["ic_all"]
