import os

from pytest import fixture, raises

from modron.characters import Character


_joe_path = os.path.join(os.path.dirname(__file__), 'joe.yaml')


@fixture
def joe() -> Character:
    return Character.from_yaml(_joe_path)


def test_level(joe):
    assert joe.level == 4
    assert joe.proficiency_bonus == 2

    # Test leveling him up
    joe.classes['fighter'] = 2
    assert joe.level == 5
    assert joe.proficiency_bonus == 3


def test_ability_mods(joe):
    assert joe.strength_mod == 2
    assert joe.dexterity_mod == -1
    assert joe.constitution_mod == 1
    assert joe.wisdom_mod == 2
    assert joe.charisma_mod == 0


def test_saving_throws(joe):
    assert joe.save_modifier('strength') == 4
    assert joe.save_modifier('dexterity') == -1


def test_skills(joe):
    # Make sure the skills are found
    assert len(joe.proficiencies) == 1
    assert 'medicine' in joe.proficiencies
    assert joe.custom_skills['tomfoolery'] == 'charisma'

    # Check the modifiers
    assert joe.skill_modifier('tomfoolery') == 0
    assert joe.skill_modifier('medicine') == 4
    assert joe.skill_modifier('athletics') == 6
    with raises(ValueError):
        assert joe.skill_modifier('not a skill')


def test_hit_die(joe):
    hit_die = joe.get_hit_die()
    assert hit_die == {'d8': 3, 'd10': 1}

    # Add a level in Paladin, which has the same hit die as his Fighter class
    joe.classes['paladin'] = 1
    hit_die = joe.get_hit_die()
    assert hit_die == {'d8': 3, 'd10': 2}


def test_lookup_modifier(joe):
    assert joe.lookup_modifier("strength") == 2
    assert joe.lookup_modifier("strength save") == 4
    assert joe.lookup_modifier("medicine") == 4
