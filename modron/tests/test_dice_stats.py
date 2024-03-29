from math import isclose

from pytest import mark
import numpy as np

from modron.dice.stats import SlantedDie, FairDie, DieModel, ExtremeDie, fit_model, DiceRollStatistics


def test_fair():
    m = FairDie(6)
    assert isclose(m.compute_likelihood(1), 1./6)
    assert np.isclose(m.compute_likelihood([1, 2]), [1. / 6] * 2).all()


def test_slanted():
    m = SlantedDie(6, 1)
    assert isclose(m.compute_likelihood(6), 1. / 6)
    for w in [0.5, 2.]:
        m.set_params([w])
        assert isclose(m.compute_likelihood(6) / m.compute_likelihood(1), w)
        assert m.description.startswith('Large' if w > 1 else 'Small')


def test_extreme():
    m = ExtremeDie(6, 1)
    assert isclose(m.compute_likelihood(6), 1. / 6)
    for w in [0.5, 2.]:
        m.set_params([w])
        assert isclose(m.compute_likelihood(6) / m.compute_likelihood(3.5), w)
        assert m.description.startswith('Extreme' if w > 1 else 'Average')


@mark.parametrize(
    'model', [FairDie(6), SlantedDie(6, 2), ExtremeDie(6, 12)]
)
def test_total_value(model: DieModel):
    assert isclose(1, np.sum(model.compute_likelihood(np.arange(1, model.n_faces + 1))))


def test_fit():
    # Test a fair dice
    r = [1, 2, 3, 4, 5, 6]
    m = SlantedDie(6)
    fit_model(r, m)
    assert np.isclose(m.get_params(), [1.]).all()

    # Test an unfair die
    r = [1, 2, 3, 6, 3, 1]
    fit_model(r, m)
    assert m.weight < 1.


def test_summary():
    rolls = [1, 2, 5, 5, 8, 12, 16, 13, 20]
    summary = DiceRollStatistics.from_rolls(20, rolls)

    # The fair die is always the least likely
    assert summary.models[-1].model_name == "FairDie"
