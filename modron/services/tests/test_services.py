import os

from pytest import fixture, mark, raises

from modron.services import ReminderService
from modron.slack import BotClient


@fixture()
def client() -> BotClient:
    token = os.environ.get('OAUTH_ACCESS_TOKEN', None)
    if token is None:
        raise ValueError('Cannot find Auth token')
    return BotClient(token=token)


@mark.timeout(60)
def test_reminder(client):
    thread = ReminderService(client, max_sleep_time=5)
    thread.stop = True

    with raises(ValueError):
        thread.run()
