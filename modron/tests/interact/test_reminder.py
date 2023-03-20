import asyncio
from asyncio import Task

from discord import Message, utils
from pytest import mark, fixture, raises

from modron.interact.reminder import ReminderModule, parse_delay
from modron.interact.followup import FollowupModule
from modron.services.reminder import ReminderService

reminders = ReminderModule()


def test_delay_parser():
    assert parse_delay('1 second').total_seconds() == 1
    with raises(ValueError) as error:
        parse_delay('asdf')
    assert 'asdf' in str(error.value)


@mark.asyncio
async def test_delay_status(payload, guild):
    # Update the state by checking for the last message
    service = ReminderService(guild, "ic_all", 853806638346534962)  # Look at all IC channels
    await service.perform_reminder_check()

    # Run a status check
    args = reminders.parser.parse_args(['status'])
    await reminders.interact(args, payload)
    assert payload.last_message.startswith('Next check')
    assert 'was from' in payload.last_message, payload.last_message


@mark.asyncio
async def test_delay_pause(payload):
    args = reminders.parser.parse_args(['break', '1 second'])
    await reminders.interact(args, payload)
    assert 'paused' in payload.last_message.lower()


@fixture()
def followup():
    return FollowupModule()


@mark.asyncio
async def test_msg_reminders(payload, followup, guild):
    # Make sure we get a default that is reasonable
    args = followup.parser.parse_args([])
    assert args.time == '3 hours'

    # Get a link to the channel used for testing
    test_channel = utils.get(guild.channels, name='bot_testing')

    # See that we follow up on the correct channel
    args = followup.parser.parse_args(['5 second'])
    task: Task = await followup.interact(args, payload)
    assert task is not None, payload.last_message
    await task
    assert task.result(), payload.last_message

    # Delete that reminder message
    await test_channel.last_message.delete()

    # Send a message between the last reminder, make sure we do not remind twice
    args.time = '30 seconds'
    task: Task = await followup.interact(args, payload)
    await asyncio.sleep(15)
    msg: Message = await test_channel.send('I did something!')
    assert task is not None, payload.last_message
    await task
    assert not task.result(), 'We sent a reminder anyway'
    await msg.delete()
