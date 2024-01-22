import os
from datetime import timedelta, datetime

from discord import Guild, utils, TextChannel
from pytest import mark

from modron.config import config
from modron.utils import get_local_tz_offset
from modron.services.backup import BackupService
from modron.services.reminder import ReminderService


@mark.timeout(60)
@mark.asyncio
async def test_reminder(guild: Guild):
    service = ReminderService(guild, "bot_testing", ["bot_testing"], max_sleep_time=5)

    # Send a message to the bot-test channel
    test_channel: TextChannel = utils.get(guild.channels, name='bot_testing')
    message = await test_channel.send('Test message')

    # Make sure the message is captured
    last_time = await service.assess_last_activity()
    assert ((message.created_at.replace(tzinfo=None) + get_local_tz_offset()) - last_time).total_seconds() < 5, \
        'Did not pick up the latest message'
    assert service.watched_channels[0].name == 'bot_testing'

    # Delete the message
    await message.delete()

    # Run a step of the loop
    wait_time = await service.perform_reminder_check()
    assert wait_time > datetime.now()


@mark.timeout(60)
@mark.asyncio
async def test_backup(guild: Guild, tmpdir):
    config.team_options[guild.id].name = 'kaluth-test'
    # Make a temporary directory
    log_dir = os.path.join(tmpdir, 'test')
    os.makedirs(log_dir, exist_ok=True)
    service = BackupService(guild,
                            log_dir,
                            timedelta(days=1),
                            channels=[863442378592878602],
                            max_sleep_time=5)

    # Make sure the path to the output folder has the correct name
    folder_id = service.get_folder_id()
    folder = service.gdrive_client.files().get(fileId=folder_id).execute()
    assert folder['name'] == 'kaluth-test'

    # Run the code
    backup_channel: TextChannel = utils.get(guild.channels, name='bot_testing')
    count = await service.backup_messages(backup_channel)
    assert count > 0

    # Run it again immediately
    count = await service.backup_messages(backup_channel)
    assert count == 0

    # Run the loop
    counts = await service.backup_all_channels()
    assert counts == {'bot_testing': 0}

    # Delete the upload folder
    service.gdrive_client.files().delete(fileId=folder_id).execute()
    folder_id = service.get_folder_id()

    # Upload once, which should get the files
    n_uploaded, file_sizes = service.upload_to_gdrive()
    assert n_uploaded == 1
    assert file_sizes > 0

    # Attempt upload again, which should skip the process
    n_uploaded, file_sizes = service.upload_to_gdrive()
    assert n_uploaded == 0
    assert file_sizes == 0

    # Send a message and then make sure it uploads an updated file
    message = await backup_channel.send(content="Testing backup message")

    count = await service.backup_messages(backup_channel)
    assert count > 0

    n_uploaded, file_sizes = service.upload_to_gdrive()
    assert n_uploaded == 1
    assert file_sizes > 0

    # Delete the test message
    await message.delete()

    # Make sure only file was created
    result = service.gdrive_client.files().list(
        q=f'"{folder_id}" in parents and trashed = false'
    ).execute()
    assert len(result['files']) == 1
