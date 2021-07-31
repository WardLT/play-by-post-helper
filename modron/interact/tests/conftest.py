from typing import Dict
import os

from pytest import fixture

from modron.slack import BotClient
from modron.interact.npc import NPCGenerator
from modron.interact.reminder import ReminderModule
from modron.interact.dice_roll import DiceRollInteraction
from modron.interact.character import CharacterSheet
from modron.interact.stats import StatisticModule
from modron.interact import attach_commands, NoExitParser, SlashCommandPayload

_test_modules = [NPCGenerator, ReminderModule, DiceRollInteraction, CharacterSheet, StatisticModule]


@fixture
def payload(clients: Dict[str, BotClient]) -> SlashCommandPayload:
    team_id, client = next(iter(clients.items()))
    return SlashCommandPayload(
        command='/modron',
        text='{... define in test if you need ...}',
        response_url='https://httpstat.us/200',
        trigger_id='yes',
        user_id=client.my_id,
        channel_id=client.get_channel_id('bot_test'),
        team_id='TP3LCSL2Z'
    )


@fixture()
def clients() -> Dict[str, BotClient]:
    token = os.environ.get('OAUTH_ACCESS_TOKENS', None)
    if token is None:
        raise ValueError('Cannot find Auth token')
    client = BotClient(token=token)
    return {client.team_id: client}


@fixture()
def parser(clients) -> NoExitParser:
    modules = [x(clients) for x in _test_modules]
    return attach_commands(modules)
