"""Utilities for evaluating the fairness of die"""
from pathlib import Path
from csv import DictReader
from typing import List, Union, Tuple, Optional

from scipy.optimize import minimize
import numpy as np


# Dice models
from modron.dice import DiceRoll


class DieModel:
    """Model for the rolls of the dice"""

    def __init__(self, n_faces: int):
        """
        Args:
            n_faces: Number of faces on the dice
        """
        self.n_faces = n_faces

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
            weight: Factor
        """
        super().__init__(n_faces)
        assert weight > 0, "The weight value must be positive"
        self.weight = weight

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


def fit_model(rolls: List[int], die_model: DieModel) -> float:
    """Fit the parameters of a die probability model

    Args:
        rolls: List of the observed rolls
        die_model: Dice model. Will be
    Returns:
        Negative log-likelihood of the dice model
    """

    # Set up the optimization problem
    def nll(x):
        die_model.set_params(x)
        return die_model.compute_neg_log_likelihood(rolls)
    fx = minimize(nll, die_model.get_params(), method='powell', bounds=die_model.get_bounds())

    # Set the parameters
    die_model.set_params(fx.x)
    return fx.fun
