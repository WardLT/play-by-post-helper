"""Utility functions for rolling dice"""
import re
from typing import List
from random import randint


_dice_regex = re.compile(r"(?P<sign>[-+]?)(?P<number>\d*)d(?P<sides>\d+)")
_modifer_regex = re.compile(r"(?P<sign>[-+])(?P<value>\d+)([^d]|$)")


def roll_die(sides: int, advantage: bool = False, disadvantage: bool = False, reroll_one: bool = False):
    """Compute the result of rolling a single die

    Follows the D&D 5e rules. (See Chapter 7 of the PHB)

    Args:
        sides (int): Number of sides on the die
        advantage (bool): Whether to perform the roll at advantage
        disadvantage (bool): Whether to perform the roll at disadvantage
        reroll_one (bool): Whether to re-roll one of the dice if either is a 1.
            Example: If I roll two 1s at advantage, I only re-roll one of the two dice.
    """
    assert not (advantage and disadvantage), "You cannot roll both at advantage and disadvantage"
    assert sides > 0, "Dice must have a nonnegative number of faces. No non-Euclidean geometry"

    if advantage or disadvantage:
        rolls = sorted([randint(1, sides), randint(1, sides)])
        if reroll_one and rolls[0] == 1:
            rolls[0] = randint(1, sides)
        return max(rolls) if advantage else min(rolls)
    else:
        # Simple logic: Not at [dis]advantage
        value = randint(1, sides)
        if reroll_one and value == 1:
            return randint(1, sides)
        return value


class DiceRoll:
    """Representation of a single dice roll.

    Follows the D&D 5e rules for dice. Consult Chapter 7 of the D&D manual for the
    """

    def __init__(self, dice: List[int], modifier: int = 0, reroll_ones: bool = False,
                 advantage: bool = False, disadvantage: bool = False):
        """Perform a dice roll

        Args:
            dice ([int]): List of dice to roll
            modifier (int): Modifier to add to the roll
            reroll_ones (bool): Whether to re-roll dice which are 1 on the first roll
            advantage (bool): Whether to roll each dice twice and take the high value
            disadvantage (bool): Whether to roll the dice twice and take the low value
        """

        assert not (advantage and disadvantage), "You cannot roll both at advantage and disadvantage"
        self.dice = dice
        self.modifier = modifier
        self.reroll_ones = reroll_ones
        self.advantage = advantage
        self.disadvantage = disadvantage

        # Make the rolls
        self.results = [roll_die(s, advantage=advantage, disadvantage=disadvantage, reroll_one=reroll_ones)
                        for s in self.dice]

        # Store the result
        self.value = sum(self.results) + self.modifier

    @classmethod
    def make_roll(cls, roll: str):
        """Make a roll given a text string describing the dice"""

        # Match the dice components
        dice = []
        for match in _dice_regex.finditer(roll):
            groups = match.groupdict()
            if groups["sign"] == "-":
                raise ValueError('We do not yet support subtracting dice off the roll')
            number = groups.get('number')
            number = 1 if number == '' else int(number)
            sides = int(groups.get('sides'))
            dice.extend([sides] * number)

        # Match the modifier
        match = _modifer_regex.search(roll)
        if match is not None:
            modifier = int(match.group(0))
        else:
            modifier = 0

        # Look for any rolling method declarations
        advantage = ' advantage' in roll
        disadvantage = ' disadvantage' in roll
        reroll_ones = 'reroll' in roll or 're-roll' in roll
        return cls(dice, modifier, reroll_ones=reroll_ones,
                   advantage=advantage, disadvantage=disadvantage)
