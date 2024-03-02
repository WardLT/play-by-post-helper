from pytest import raises, fixture, mark

from modron.characters import Character
from modron.interact.character import CharacterSheet, HPTracker


@fixture(autouse=True)
def backup_sheet(test_sheet_path):
    """Keep track of what the original health of the test character sheet"""
    # Load in the
    with open(test_sheet_path) as fp:
        _original_sheet = fp.read()
    yield True
    with open(test_sheet_path, 'w') as fp:
        fp.write(_original_sheet)


@mark.asyncio
async def test_character(payload):
    character = CharacterSheet()
    parser = character.parser

    # Test with a real player
    args = parser.parse_args([])
    await character.interact(args, payload)
    assert "Modron" in payload.last_message

    # Test looking up an ability
    args = parser.parse_args(['ability', 'str'])
    await character.interact(args, payload)
    assert '+0' in payload.last_message


@mark.asyncio
async def test_lookup_hp(payload):
    hp = HPTracker()
    args = hp.parser.parse_args([])
    await hp.interact(args, payload)
    assert 'Modron has ' in payload.last_message


@mark.asyncio
async def test_overrule_character_choice(payload):
    hp = HPTracker()
    args = hp.parser.parse_args(['-c', 'modron'])
    await hp.interact(args, payload)
    assert 'Modron has ' in payload.last_message

    with raises(ValueError) as ex:
        args = hp.parser.parse_args(['-c', 'imp'])
        await hp.interact(args, payload)
    assert 'imp' in str(ex)

    with raises(ValueError) as ex:
        args = hp.parser.parse_args(['-c', 'adrianna'])
        await hp.interact(args, payload)
    assert 'adrianna' in str(ex)


@mark.asyncio
async def test_change_active(payload):
    character = CharacterSheet()

    # List the possible choices
    args = character.parser.parse_args(['list'])
    await character.interact(args, payload)
    assert ': modron (_active_)' in payload.last_message

    # Set a new one
    args = character.parser.parse_args(["set", "modron"])
    await character.interact(args, payload)
    assert 'Set your active character to modron' in payload.last_message

    # Try to set one you're not allowed to
    args = character.parser.parse_args(["set", "imp"])
    await character.interact(args, payload)
    assert 'imp is not within'


@mark.asyncio
async def test_harm_and_heal(payload, test_sheet_path):
    hp = HPTracker()

    # Fully heal the character
    args = hp.parser.parse_args(['heal', 'full'])
    await hp.interact(args, payload)
    assert 'hit point maximum' in payload.last_message

    # Reset the temporary hit points and HP maximum
    args = hp.parser.parse_args(['max', 'reset'])
    await hp.interact(args, payload)
    assert 'Reset hit point' in payload.last_message

    args = hp.parser.parse_args(['temp', 'reset'])
    await hp.interact(args, payload)
    assert 'Removed all temporary hit' in payload.last_message

    # Test applying damage
    args = hp.parser.parse_args(['harm', '2'])
    await hp.interact(args, payload)
    assert '2 hit points' in payload.last_message

    sheet = Character.from_yaml(test_sheet_path)
    assert sheet.total_hit_points == sheet.hit_points - 2

    # Test healing
    args = hp.parser.parse_args(['heal', '1'])
    await hp.interact(args, payload)
    assert '1 hit points' in payload.last_message

    sheet = Character.from_yaml(test_sheet_path)
    assert sheet.total_hit_points == sheet.hit_points - 1

    # Test adding temporary hit points
    args = hp.parser.parse_args(['temp', '2'])
    await hp.interact(args, payload)
    assert '2 temporary hit points' in payload.last_message

    sheet = Character.from_yaml(test_sheet_path)
    assert sheet.total_hit_points == sheet.hit_points + 1
    assert sheet.temporary_hit_points == 2

    # Test lowering hit point max
    args = hp.parser.parse_args(['max', '-2'])
    await hp.interact(args, payload)
    assert 'by -2 hit points' in payload.last_message

    sheet = Character.from_yaml(test_sheet_path)
    assert sheet.total_hit_points == sheet.hit_points
    assert sheet.temporary_hit_points == 2

    # Make sure the parse error works for all subcommands that
    #  accept a non-text input as well (e.g., 'reset')
    for sub in ['heal', 'temp', 'max']:
        args = hp.parser.parse_args([sub, 'asdf'])
        with raises(ValueError):
            await hp.interact(args, payload)


@mark.asyncio
async def test_aliases(payload, test_sheet_path):
    character = CharacterSheet()
    parser = character.parser

    args = parser.parse_args(['roll', 'list'])
    await character.interact(args, payload)
    assert payload.last_message.startswith('Available rolls')

    args = parser.parse_args(['roll', 'set', 'damage', '1d6+str'])
    await character.interact(args, payload)
    assert payload.last_message.startswith('Set damage to mean "1d6+str')
    assert 'damage' in Character.from_yaml(test_sheet_path).roll_aliases

    args = parser.parse_args(['roll', 'remove', 'damage'])
    await character.interact(args, payload)
    assert payload.last_message.startswith('Removed damage')

    args = parser.parse_args(['roll', 'list'])
    await character.interact(args, payload)
    assert 'damage' not in payload.last_message
