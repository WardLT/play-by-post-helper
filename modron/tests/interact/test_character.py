from time import sleep
import logging

from pytest import raises, fixture

from modron.characters import Character
from modron.config import get_config
from modron.interact import NoExitParserError, handle_generic_slash_command


@fixture()
def test_sheet_path():
    config = get_config()
    return config.get_character_sheet_path('TP3LCSL2Z', 'adrianna')


@fixture(autouse=True)
def backup_sheet(test_sheet_path):
    """Keep track of what the original health of the test character sheet"""
    # Load in the
    with open(test_sheet_path) as fp:
        _original_sheet = fp.read()
    yield True
    with open(test_sheet_path, 'w') as fp:
        fp.write(_original_sheet)


def test_character(parser, payload, caplog):
    # Test with the bot user, who has no characters
    args = parser.parse_args(['character'])
    with caplog.at_level(logging.INFO):
        args.roller(args, payload)
    assert "No character" in caplog.messages[-1]

    # Test with a real player
    payload.user_id = 'UP4K437HT'
    with caplog.at_level(logging.INFO):
        args.roller(args, payload)
    assert "Adrianna" in caplog.messages[-2]
    assert "Reminding" in caplog.messages[-1]

    # Test looking up an ability
    with caplog.at_level(logging.INFO):
        args = parser.parse_args(['character', 'ability', 'str'])
        args.roller(args, payload)
    assert '+3' in caplog.messages[-1]


def test_help(parser, payload, caplog):
    """Make sure the help printing works"""
    with raises(NoExitParserError) as exc:
        parser.parse_args(['character', 'ability', '--help'])
    print(exc.value.text_output)
    assert exc.value.text_output.startswith('*usage*: /modron character')


def test_lookup_hp(parser, payload, caplog):
    payload.user_id = 'UP4K437HT'
    args = parser.parse_args(['character', 'hp'])
    with caplog.at_level(logging.INFO):
        args.roller(args, payload)
    assert caplog.messages[-1].startswith('No changes.')


def test_harm_and_heal(parser, payload, caplog, test_sheet_path):
    payload.user_id = 'UP4K437HT'

    # Fully heal the character
    args = parser.parse_args(['character', 'hp', 'heal', 'full'])
    with caplog.at_level(logging.INFO):
        args.roller(args, payload)
    assert caplog.messages[-1].startswith('Saved')
    assert 'Fully healed' in caplog.messages[-2]

    # Reset the temporary hit points and HP maximum
    args = parser.parse_args(['character', 'hp', 'max', 'reset'])
    with caplog.at_level(logging.INFO):
        args.roller(args, payload)
    assert 'Reset hit point' in caplog.messages[-2]

    args = parser.parse_args(['character', 'hp', 'temp', 'reset'])
    with caplog.at_level(logging.INFO):
        args.roller(args, payload)
    assert 'Removed all temporary hit' in caplog.messages[-2]

    # Test applying damage
    args = parser.parse_args(['character', 'hp', 'harm', '10'])
    with caplog.at_level(logging.INFO):
        args.roller(args, payload)
    assert '10 hit points' in caplog.messages[-2]

    sheet = Character.from_yaml(test_sheet_path)
    assert sheet.total_hit_points == sheet.hit_points - 10

    # Test healing
    args = parser.parse_args(['character', 'hp', 'heal', '5'])
    with caplog.at_level(logging.INFO):
        args.roller(args, payload)
    assert '5 hit points' in caplog.messages[-2]

    sheet = Character.from_yaml(test_sheet_path)
    assert sheet.total_hit_points == sheet.hit_points - 5

    # Test adding temporary hit points
    args = parser.parse_args(['character', 'hp', 'temp', '2'])
    with caplog.at_level(logging.INFO):
        args.roller(args, payload)
    assert '2 temporary hit points' in caplog.messages[-2]

    sheet = Character.from_yaml(test_sheet_path)
    assert sheet.total_hit_points == sheet.hit_points - 3
    assert sheet.temporary_hit_points == 2

    # Test lowering hit point max
    args = parser.parse_args(['character', 'hp', 'max', '-22'])
    with caplog.at_level(logging.INFO):
        args.roller(args, payload)
    assert 'by -22 hit points' in caplog.messages[-2]

    sheet = Character.from_yaml(test_sheet_path)
    assert sheet.total_hit_points == sheet.hit_points - 20
    assert sheet.temporary_hit_points == 2

    # Make sure the parse error works for all subcommands that
    #  accept a non-text input as well (e.g., 'reset')
    for sub in ['heal', 'temp', 'max']:
        args = parser.parse_args(['character', 'hp', sub, 'asdf'])
        with caplog.at_level(logging.INFO):
            args.roller(args, payload)
        assert 'Parse error' in caplog.messages[-1]


def test_hp_shortcut(payload, parser, caplog):
    # Special shortcut for /roll
    payload.command = '/hp'
    payload.text = ''
    payload.user_id = 'UP4K437HT'
    with caplog.at_level(logging.INFO):
        assert handle_generic_slash_command(payload, parser) == {"response_type": "in_channel"}
        sleep(5)  # Waits for the delayed thread to run
    assert caplog.messages[-1].startswith('No changes.')
