import os
from datetime import timedelta

from pytest import fixture, mark, raises

from modron.services.backup import BackupService
from modron.services.reminder import ReminderService
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


@mark.timeout(60)
def test_backup(client, tmpdir):
    thread = BackupService(client, tmpdir, timedelta(days=1), channel_regex='^bot_test$',
                           max_sleep_time=5)

    # Run the code
    count = thread.backup_messages('bot_test')
    assert count > 0

    # Run it again immediately
    count = thread.backup_messages('bot_test')
    assert count == 0

    # Run the loop
    counts = thread.backup_all_channels()
    assert counts == {'bot_test': 0}

    # Make sure the infinite loop works
    thread.stop = True
    with raises(ValueError):
        thread.run()
