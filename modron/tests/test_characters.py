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
    assert joe.lookup_modifier("str save") == 4
    assert joe.lookup_modifier("medicine") == 4


def test_skill_list(joe):
    skills = joe.get_skills_by_ability("strength")
    assert skills["athletics"] == "expert"
    assert len(skills) == 1

    skills = joe.get_skills_by_ability("charisma")
    assert skills["tomfoolery"] == "untrained"

    skills = joe.get_skills_by_ability("wisdom")
    assert skills["medicine"] == "proficient"


def test_hp_changes(joe):
    # Make sure it starts out at full health
    assert joe.current_hit_points == joe.hit_points

    # Make sure over-healing does not go above maximum
    joe.heal(1)
    assert joe.current_hit_points == joe.hit_points

    # Test out damage
    joe.harm(1)
    assert joe.current_hit_points + 1 == joe.hit_points

    # Make sure the damage stops at zero
    joe.harm(joe.current_hit_points * 2)
    assert joe.current_hit_points == 0

    # Test healing
    joe.heal(1)
    assert joe.current_hit_points == 1

    # Test the "full heal"
    joe.full_heal()
    assert joe.current_hit_points == joe.hit_points


def test_temporary_hit_points(joe):
    # Give some temporary hit points
    joe.grant_temporary_hit_points(4)
    assert joe.temporary_hit_points == 4
    assert joe.total_hit_points == joe.current_hit_points + 4
    assert joe.current_hit_points == joe.hit_points

    # Make sure damage less than the temp only comes from the temp
    joe.harm(2)
    assert joe.temporary_hit_points == 2
    assert joe.total_hit_points == joe.current_hit_points + 2
    assert joe.current_hit_points == joe.hit_points

    # Make sure damage that exceeds the temp hits both
    joe.harm(4)
    assert joe.temporary_hit_points == 0
    assert joe.total_hit_points == joe.current_hit_points
    assert joe.current_hit_points == joe.hit_points - 2

    # Damage his hit point maximum
    joe.adjust_hit_point_maximum(-16)
    assert joe.current_hit_point_maximum == joe.hit_points - 16
    assert joe.current_hit_points == joe.current_hit_point_maximum

    # Ensure that you cannot heal above it
    joe.heal(1)
    assert joe.current_hit_point_maximum == joe.hit_points - 16
    assert joe.current_hit_points == joe.current_hit_point_maximum

    # Update the maximum, which should not change the hit points
    joe.adjust_hit_point_maximum(1)
    assert joe.current_hit_point_maximum == joe.hit_points - 15
    assert joe.current_hit_points == joe.current_hit_point_maximum - 1

    # Reset
    joe.reset_hit_point_maximum()
    assert joe.current_hit_point_maximum == joe.hit_points


def test_jack_of_all_trades(joe):
    # Make Joe a bard
    joe.classes['bard'] = 2

    # Test initiative
    assert joe.initiative == joe.dexterity_mod + joe.proficiency_bonus // 2
    assert joe.lookup_modifier('initiative') == joe.dexterity_mod + joe.proficiency_bonus // 2

    # No additional bonus to proficient skills
    assert joe.skill_modifier('medicine') == joe.wisdom_mod + joe.proficiency_bonus
    assert joe.skill_modifier('athletics') == joe.strength_mod + joe.proficiency_bonus * 2

    # But a bonus to others
    assert joe.skill_modifier('insight') == joe.wisdom_mod + joe.proficiency_bonus // 2
