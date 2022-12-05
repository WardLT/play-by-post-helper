"""Utilities for evaluating the fairness of die"""
from typing import List, Union, Tuple

from scipy.linalg import solve
from scipy.optimize import minimize
from pydantic import BaseModel, Field
import numpy as np


def _pretty_multiplier(x: float) -> str:
    """Make a prettier version of a multiplier value

    Args:
        x: Value for a multiplicative factor (e.g., b = x * a)
    Returns:
        A humanized version of it
    """
    if x > 100:
        return f'{x:.0f}x'
    elif x > 2:
        return f'{x:.1f}x'
    return f'{(x-1)*100:.1f}%'


# Dice models
class DieModel:
    """Model for the rolls of the dice"""

    def __init__(self, n_faces: int):
        """
        Args:
            n_faces: Number of faces on the dice
        """
        self.n_faces = n_faces

    @property
    def description(self) -> str:
        raise NotImplementedError()

    @property
    def likelihoods(self) -> List[float]:
        return self.compute_likelihood(np.arange(1, self.n_faces + 1)).tolist()

    def get_params(self) -> List[float]:
        """Get the parameters for the model

        Returns:
            List of the parameters
        """
        raise NotImplementedError()

    def set_params(self, x: List[float]):
        """Set the parameters for this model of the dice"""
        raise NotImplementedError()

    def get_bounds(self) -> List[Tuple[float, float]]:
        """Get the allowed bounds for the parameters"""
        raise NotImplementedError()

    def compute_likelihood(self, rolls: Union[np.ndarray, int, List[int]]) -> np.ndarray:
        """Compute the likelihood of one or more dice rolls

        Args:
            rolls: The roll value(s)
        Returns:
            The probability of those rolls
        """
        raise NotImplementedError()

    def compute_neg_log_likelihood(self, rolls: List[int]) -> float:
        """Compute the negative log likelihood of a certain set of dice rolls

        Args:
            rolls: Observed rolls
        Returns:
            Log-likelihood of the outcome
        """
        probs = self.compute_likelihood(rolls)
        return -np.log(probs).sum()


class FairDie(DieModel):
    """Model for a fair dice"""

    @property
    def description(self) -> str:
        return "A fair die."

    def get_params(self) -> List[float]:
        return []

    def set_params(self, x: List[float]):
        return

    def get_bounds(self) -> List[Tuple[float, float]]:
        return []

    def compute_likelihood(self, rolls: Union[np.ndarray, int, List[int]]) -> np.ndarray:
        x = np.zeros_like(rolls, dtype=np.float)
        x += 1. / self.n_faces
        return x


class SlantedDie(DieModel):
    """Model for a die that probabilities linearly increase or decrease in value"""

    def __init__(self, n_faces: int, weight: float = 1):
        """
        Args:
            n_faces: Number of faces on the dice
            weight: Large values are this factor more likely than small values
        """
        super().__init__(n_faces)
        assert weight > 0, "The weight value must be positive"
        self.weight = weight

    @property
    def description(self) -> str:
        if self.weight > 1:
            return f"Large values are {_pretty_multiplier(self.weight)} more likely than small."
        else:
            return f"Small values are {_pretty_multiplier(1. / self.weight)} more likely than large."

    def get_params(self) -> List[float]:
        return [self.weight]

    def set_params(self, x: List[float]):
        self.weight, = x

    def get_bounds(self) -> List[Tuple[float, float]]:
        return [(0.001, 1000)]

    def compute_likelihood(self, rolls: Union[np.ndarray, int, List[int]]) -> np.ndarray:
        # Get slope the low- and high-values
        start = 2. / (self.weight + 1)
        slope = (self.weight * start - start) / (self.n_faces - 1)

        # Compute the probability for each roll
        return np.multiply(1. / self.n_faces, start + np.multiply(slope, np.subtract(rolls, 1)))


class ExtremeDie(DieModel):
    """Die that prefer to roll extreme values"""

    def __init__(self, n_faces: int, extremity: float = 1):
        """
        Args:
            n_faces: Number of faces on the die
            extremity: Ratio between extreme and middle value
        """
        super().__init__(n_faces)
        self.extremity = extremity

    @property
    def description(self) -> str:
        if self.extremity > 1:
            return f"Extreme values are {_pretty_multiplier(self.extremity)} more likely than average."
        else:
            return f"Average values are {_pretty_multiplier(1. / self.extremity)} more likely than extreme."

    def set_params(self, x: List[float]):
        self.extremity, = x

    def get_params(self) -> List[float]:
        return [self.extremity]

    def get_bounds(self) -> List[Tuple[float, float]]:
        return [(0.001, 1000)]

    def compute_likelihood(self, rolls: Union[np.ndarray, int, List[int]]) -> np.ndarray:
        # Compute the curvature
        #  Let m be the average value: m = (d - 1) / 2 + 1 = 0.5 * (d + 1)
        #  Assume p(x) ~ a * (x - m) ** 2 + c
        #  Let p(1) = e * p(m)
        #   a * (1 - m) ** 2 + c = e * c
        #  Eq 1: (1 - m) ** 2 * a - (1 - e) * c = 0
        #  Let: sum_i=1^d p(i) = 1
        #  Eq 2: a * sum_i=1^d (i - m) ** 2 + d * c = 1
        m = 0.5 * (self.n_faces + 1)
        a, c = solve([
            [(1 - m) ** 2, 1 - self.extremity],
            [np.power(np.arange(1, self.n_faces + 1) - m, 2).sum(), self.n_faces]
        ], [0, 1])

        return a * np.power(np.subtract(rolls, m), 2) + c


def fit_model(rolls: List[int], die_model: DieModel) -> float:
    """Fit the parameters of a die probability model

    Args:
        rolls: List of the observed rolls
        die_model: Dice model. Will be
    Returns:
        Negative log-likelihood of the dice model
    """

    # Special case: FairDie
    if isinstance(die_model, FairDie):
        return die_model.compute_neg_log_likelihood(rolls)

    # Set up the optimization problem
    def nll(x):
        die_model.set_params(x)
        return die_model.compute_neg_log_likelihood(rolls)
    fx = minimize(nll, die_model.get_params(), method='powell', bounds=die_model.get_bounds())

    # Set the parameters
    die_model.set_params(fx.x)
    return fx.fun


# Summary functions
class DieModelSummary(BaseModel):
    """Results of a dice model fitting"""

    model_name: str = Field(..., description="Name of the model")
    nll: float = Field(..., description="Negative log-likelihood of the model fitting")
    description: str = Field(..., description="Short description for the model")
    likelihoods: List[float] = Field(..., description="Likelihoods for each value of die")

    @classmethod
    def from_fitting(cls, rolls: List[int], model: DieModel) -> 'DieModelSummary':
        """Create a die summary

        Args:
            model: Model to fit and summarize
            rolls: Observed rolls
        """

        # Fit the model
        nll = fit_model(rolls, model)

        # Create the summary
        return cls(
            model_name=model.__class__.__name__,
            nll=nll,
            description=model.description,
            likelihoods=model.likelihoods
        )


class DiceRollStatistics(BaseModel):
    """Statistics about dice rolls"""

    rolls: List[int] = Field(..., description="Values of all of the rolls")
    num_faces: int = Field(..., description="Number of faces on the die")
    models: List[DieModelSummary] = Field(..., description="Description of the models. Sorted by fitness")

    @classmethod
    def from_rolls(cls, num_faces: int, rolls: List[int]) -> 'DiceRollStatistics':
        """Generate a summary of a series of rolls

        Args:
            num_faces: Number of faces on the die
            rolls: Value of the rolls
        """

        # Run the models
        fits = [DieModelSummary.from_fitting(rolls, model)
                for model in [FairDie(num_faces), SlantedDie(num_faces), ExtremeDie(num_faces)]]
        fits = sorted(fits, key=lambda x: x.nll)  # Sort by fitness

        return DiceRollStatistics(
            rolls=rolls,
            num_faces=num_faces,
            models=fits
        )
