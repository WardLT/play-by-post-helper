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


@fixture
def user_id(client) -> str:
    """ID of the first user, Slackbot"""
    result = client.users_list()
    return result['members'][0]['id']


def test_channel_match(client):
    matched = client.match_channels("ic_all")
    assert matched == ["ic_all"]


def test_channel_name(client):
    cid = client.get_channel_id("ic_all")
    cname = client.get_channel_name(cid)
    assert cname == "ic_all"


def test_display_name(client, user_id):
    # Pick a user at random
    my_name = client.get_user_name(user_id)
    assert my_name == 'Slackbot'
