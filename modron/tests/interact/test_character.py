from time import sleep
import logging

from discord import Guild
from pytest import raises, fixture, mark

from modron.characters import Character
from modron.config import get_config
from modron.interact import NoExitParserError, handle_generic_slash_command
from modron.interact.character import CharacterSheet, HPTracker


@fixture()
def test_sheet_path(guild: Guild):
    config = get_config()
    return config.get_character_sheet_path(guild.id, 'modron')


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
