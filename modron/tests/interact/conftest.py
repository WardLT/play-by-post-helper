from discord import TextChannel, Guild, Message, Member
from discord import utils
from pytest_asyncio import fixture as async_fixture

from modron.interact.dice_roll import DiceRollInteraction

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


@async_fixture
async def payload(guild: Guild) -> MockContext:
    """Build a fake context"""
    author = guild.get_member(862094786956886035)  # Modron
    channel = utils.get(guild.channels, name='bot_testing')
    return MockContext(
        author=author,
        guild=guild,
        channel=channel
    )
