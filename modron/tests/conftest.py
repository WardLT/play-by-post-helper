from pathlib import Path
import asyncio
import os

from discord import Guild, Intents
from pytest_asyncio import fixture as async_fixture
from pytest import fixture

from modron.bot import ModronClient


@fixture()
def guild_id() -> int:
    """ID of repo used for testing"""
    return 853806073906593832


@fixture()
def player_id() -> int:
    """ID of player used """
    return 854826609101111317


@fixture()
def repo_root() -> Path:
    return Path(__file__).parents[2]


@fixture()
def run_in_repo_root(repo_root):
    """Runs a test in the repo root where it can find config files

    Must be a nondestructive test"""
    cwd = Path.cwd()
    os.chdir(repo_root)
    yield
    os.chdir(cwd)


@async_fixture()
async def bot() -> ModronClient:
    token = os.environ.get('BOT_TOKEN', None)
    if token is None:
        raise ValueError('Cannot find Auth token')
    client = ModronClient(command_prefix="/", intents=Intents.default())
    client.testing = True

    # Log in to the service
    await client.login(token)

    # Launch the connection
    task = asyncio.create_task(client.connect())
    await client.wait_until_ready()

    # Give the client, but make sure to kill it later
    yield client
    await client.close()
    task.result()


@async_fixture()
async def guild(bot: ModronClient, guild_id) -> Guild:
    return bot.get_guild(guild_id)
