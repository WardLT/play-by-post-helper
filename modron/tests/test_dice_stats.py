from math import isclose

from pytest import mark
import numpy as np

from modron.dice.stats import SlantedDie, FairDie, DieModel, fit_model


def test_fair():
    m = FairDie(6)
    assert isclose(m.compute_likelihood(1), 1./6)
    assert np.isclose(m.compute_likelihood([1, 2]), [1. / 6] * 2).all()


def test_slanted():
    m = SlantedDie(6, 1)
    assert isclose(m.compute_likelihood(6), 1. / 6)
    for w in [0.5, 1., 2.]:
        m.set_params([w])
        assert isclose(m.compute_likelihood(6) / m.compute_likelihood(1), w)


@mark.parametrize(
    'model', [FairDie(6), SlantedDie(6, 2)]
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
    print(m.weight)
    assert m.weight < 1.
