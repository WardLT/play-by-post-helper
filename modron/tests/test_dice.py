from modron.dice import roll_die, DiceRoll
from math import isclose
from random import seed

seed(1)
_default_rolls = 10 ** 6


def _measure_probability(sides: int, target_val: int, n_trials: int = _default_rolls, **kwargs) -> float:
    """Measure the probability of a certain dice roll

    Args:
        sides (int): Number of sides on the die
        n_trials (int): Number of times to simulate the roll
        target_val (int): Target value of the dice
        **kwargs: Any modifiers to the dice roll
    Returns:
        (float) Fraction of rolls that were the target value
    """

    # Using a functional notation to avoid storing the whole array
    hits = sum(map(lambda x: roll_die(sides, **kwargs)[0] == target_val, range(n_trials)))
    return hits / n_trials


def test_simple_roll():
    assert isclose(_measure_probability(2, 1), 0.5, abs_tol=1e-3)


def test_reroll_one():
    assert isclose(_measure_probability(6, 1, reroll_one=True), 1 / 36, abs_tol=1e-3)


def test_advantage():
    assert isclose(_measure_probability(2, 2, advantage=True), 0.75, abs_tol=1e-3)


def test_disadvantage():
    assert isclose(_measure_probability(2, 2, disadvantage=True), 0.25, abs_tol=1e-3)


def test_advantage_reroll():
    assert isclose(_measure_probability(2, 2, advantage=True, reroll_one=True),
                   1 - (0.25 * 0.5), abs_tol=1e-3)


def test_parser():
    # Simple 1d20
    roll = DiceRoll.make_roll('1d20')
    assert roll.dice == [20]
    assert not roll.advantage
    assert not roll.disadvantage
    assert not roll.reroll_ones
    assert roll.value == roll.results[0][0]

    # d20 with modifier
    roll = DiceRoll.make_roll('d20-2')
    assert roll.dice == [20]
    assert not roll.advantage
    assert not roll.disadvantage
    assert not roll.reroll_ones
    assert roll.value == roll.results[0][0] - 2

    # Test several dice rolls with re-rolling
    roll = DiceRoll.make_roll('d3+4d14+2', reroll_ones=True)
    assert str(roll).startswith('4d14+1d3+2 re-rolling ones =')
    assert roll.dice == [3, 14, 14, 14, 14]
    assert not roll.advantage
    assert not roll.disadvantage
    assert roll.reroll_ones
    assert roll.value == sum([x[0] for x in roll.results]) + 2

    # Test advantage and disadvantage
    roll = DiceRoll.make_roll('d20+2', advantage=True)
    assert str(roll).startswith('1d20+2 at advantage =')
    assert roll.dice == [20]
    assert roll.advantage
    assert not roll.disadvantage

    roll = DiceRoll.make_roll('d20+2', disadvantage=True)
    assert roll.dice == [20]
    assert not roll.advantage
    assert roll.disadvantage
