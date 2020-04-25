import os

import yaml
from pytest import fixture, raises

from modron.characters import Character


_joe_path = os.path.join(os.path.dirname(__file__), 'joe.yaml')


@fixture
def joe() -> Character:
    with open(_joe_path) as fp:
        return Character.parse_obj(yaml.load(fp))


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
    assert joe.skill_mod('tomfoolery') == 0
    assert joe.skill_mod('medicine') == 4
    assert joe.skill_mod('athletics') == 6
    with raises(ValueError):
        assert joe.skill_mod('not a skill')
