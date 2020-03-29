"""Tests related to the Slack API"""
import os

from pytest import fixture

from modron.slack import BotClient


@fixture()
def client() -> BotClient:
    token = os.environ.get('OAUTH_ACCESS_TOKEN', None)
    if token is None:
        raise ValueError('Cannot find Auth token')
    return BotClient(token=token)


def test_channel_match(client):
    matched = client.match_channels("ic_all")
    assert matched == ["ic_all"]
