from pytest import mark

from modron.interact.reminder import ReminderModule
from modron.services.reminder import ReminderService

rem = ReminderModule()


@mark.asyncio
async def test_delay_status(payload, guild):
    # Update the state by checking for the last message
    service = ReminderService(guild, "ic_all", 853806638346534962)  # Look at all IC channels
    await service.assess_last_activity()

    # Run a status check
    args = rem.parser.parse_args(['status'])
    await rem.interact(args, payload)
    assert payload.last_message.startswith('Next check')
    assert 'was from' in payload.last_message, payload.last_message


@mark.asyncio
async def test_delay_pause(payload):
    args = rem.parser.parse_args(['break', 'PT1S'])
    await rem.interact(args, payload)
    assert 'paused' in payload.last_message.lower()
