import asyncio
import os

from discord import Guild
from pytest import fixture

from modron.bot import ModronClient


@fixture()
async def client() -> ModronClient:
    token = os.environ.get('BOT_TOKEN', None)
    if token is None:
        raise ValueError('Cannot find Auth token')
    client = ModronClient(command_prefix="/")

    # Log in to the service
    await client.login(token)

    # Launch the connection
    task = asyncio.create_task(client.connect())
    await client.wait_until_ready()

    # Give the client, but make sure to kill it later
    yield client
    task.cancel()


@fixture()
async def guild(client: ModronClient) -> Guild:
    return client.get_guild(853806073906593832)
