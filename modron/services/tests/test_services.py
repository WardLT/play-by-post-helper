import os
from datetime import timedelta

from pytest import fixture, mark, raises

from modron.config import get_config
from modron.services.backup import BackupService
from modron.services.reminder import ReminderService
from modron.slack import BotClient

config = get_config()


@fixture()
def client() -> BotClient:
    token = os.environ.get('OAUTH_ACCESS_TOKENS', None)
    if token is None:
        raise ValueError('Cannot find Auth token')
    return BotClient(token=token)


@mark.timeout(60)
def test_reminder(client):
    thread = ReminderService(client, "bot_test", "bot_test", max_sleep_time=5)
    thread.stop = True

    with raises(ValueError):
        thread.run()


@mark.timeout(60)
def test_backup(client, tmpdir):
    # Make a temporary directory
    log_dir = os.path.join(tmpdir, 'test_slack')
    os.makedirs(log_dir, exist_ok=True)
    thread = BackupService(client, log_dir, timedelta(days=1), channel_regex='^bot_test$',
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

    # Delete the previously-uploaded folder
    result = thread.gdrive_service.files().list(
        q=f"name = 'test_slack' and '{config.gdrive_backup_folder}' in parents and trashed = false",
        pageSize=1
    ).execute()
    hits = result.get('files', [])
    if len(hits) == 1:
        thread.gdrive_service.files().delete(fileId=hits[0]['id']).execute()

    # Upload once, which should get the files
    n_uploaded, file_sizes = thread.upload_to_gdrive()
    assert n_uploaded == 1
    assert file_sizes > 0

    # Attempt upload again, which should skip the process
    n_uploaded, file_sizes = thread.upload_to_gdrive()
    assert n_uploaded == 0
    assert file_sizes == 0

    # Send a message and then make sure it uploads an updated file
    channel_id = client.get_channel_id("bot_test")
    client.chat_postMessage(channel=channel_id, text="Test message")

    count = thread.backup_messages('bot_test')
    assert count == 1

    n_uploaded, file_sizes = thread.upload_to_gdrive()
    assert n_uploaded == 1
    assert file_sizes > 0

    # Make sure the infinite loop works
    thread.stop = True
    with raises(ValueError):
        thread.run()
