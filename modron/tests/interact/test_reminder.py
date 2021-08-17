from pytest import mark

from modron.interact.reminder import ReminderModule

rem = ReminderModule()


@mark.asyncio
async def test_delay_status(payload):
    args = rem.parser.parse_args(['status'])
    await rem.interact(args, payload)
    assert payload.last_message.startswith('Next check')


@mark.asyncio
async def test_delay_pause(payload):
    args = rem.parser.parse_args(['break', 'PT1S'])
    await rem.interact(args, payload)
    assert 'paused' in payload.last_message.lower()
