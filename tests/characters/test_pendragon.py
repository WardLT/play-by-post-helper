from pathlib import Path

from pytest import fixture

from modron.characters.pendragon import PendragonCharacter

_alek_path = Path(__file__).parent / '../../characters/pendragon/alek.yml'


@fixture()
def alek() -> PendragonCharacter:
    return PendragonCharacter.from_yaml(_alek_path)


def test_traits(alek):
    """Make sure the traits all add to 20!"""

    pairs = [
        ('chaste', 'lustful'), ('energetic', 'lazy'), ('forgiving', 'vengeful'), ('generous', 'selfish'),
        ('honest', 'deceitful'), ('just', 'arbitrary'), ('merciful', 'cruel'), ('modest', 'proud'),
        ('prudent', 'reckless'), ('spiritual', 'worldly'), ('temperate', 'indulgent'), ('trusting', 'suspicious'),
        ('valorous', 'cowardly')
    ]
    for virtue, vice in pairs:
        assert getattr(alek.traits, virtue) + getattr(alek.traits, vice) == 20

    assert alek.traits.get_religious_bonus('christian') == 13 + 10 + 10 + 13 + 14 + 8
    assert alek.traits.get_religious_bonus('pagan') == 15 + 13 + 16 + 7 + 7 + 8
    assert alek.traits.get_religious_bonus('wodinic') == 13 + 6 + 7 + 11 + 15 + 12

    assert alek.traits.chivalry_bonus == 15 + 13 + 8 + 10 + 13 + 15


def test_passions(alek):
    assert alek.passions.hate is None
    assert alek.passions.concern_commoners == 6
    assert 'concern_commoners' in alek.passions.dict()


def test_statistics(alek):
    assert alek.statistics.damage == 4
    assert alek.statistics.healing_rate == 3
    assert alek.statistics.move_rate == 16
    assert alek.statistics.hit_point_max == 27
    assert alek.statistics.unconscious == 6
    assert alek.statistics.major_wound == 17
