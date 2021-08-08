from typing import Dict

from discord import TextChannel, Guild, Message, Member
from discord import utils
from pytest import fixture

# from modron.interact.npc import NPCGenerator
# from modron.interact.reminder import ReminderModule
from modron.bot import ModronClient
from modron.interact.dice_roll import DiceRollInteraction
# from modron.interact.character import CharacterSheet
# from modron.interact.stats import StatisticModule
from modron.interact import attach_commands, NoExitParser

_test_modules = [DiceRollInteraction]


class MockContext:
    """Context where we don't actually send anything to Discord"""

    def __init__(self, guild: Guild, author: Member, channel: TextChannel):
        self.author = author
        self.guild = guild
        self.channel = channel
        self.last_message = None

    async def send(self, content=None, *, tts=False, embed=None, file=None,
                   files=None, delete_after=None, nonce=None,
                   allowed_mentions=None, reference=None,
                   mention_author=None):
        self.last_message = content

    async def reply(self, content=None, **kwargs):
        self.last_message = content


class MockMessage(Message):
    pass


@fixture
async def payload(guild: Guild) -> MockContext:
    """Build a fake context"""
    author = guild.members[0]
    channel = utils.get(guild.channels, name='bot_testing')
    return MockContext(
        author=author,
        guild=guild,
        channel=channel
    )
