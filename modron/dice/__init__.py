"""Utility functions for rolling dice"""
import re
from typing import List, Tuple, Sequence
from random import randint
from collections import Counter

dice_regex = re.compile(r"(?P<sign>[-+]?)(?P<number>\d*)d(?P<sides>\d+)")
_modifer_regex = re.compile(r"(?P<sign>[-+])(?P<value>\d+)([^d]|$)")


def roll_die(sides: int,
             advantage: bool = False,
             disadvantage: bool = False,
             reroll_one: bool = False,
             reroll_two: bool = False) \
        -> Tuple[int, Sequence[int]]:
    """Compute the result of rolling a single die

    Follows the D&D 5e rules. (See Chapter 7 of the PHB)

    Args:
        sides (int): Number of sides on the die
        advantage (bool): Whether to perform the roll at advantage
        disadvantage (bool): Whether to perform the roll at disadvantage
        reroll_one (bool): Whether to re-roll values of 1. Only re-rolls one of two dice if using
            advantage or disadvantage.
            Example: If I roll two 1s at advantage, I only re-roll one of the two dice.
        reroll_two (bool): Whether to re-roll values of 1 or 2. Takes precedent over ``reroll_ones``.
            As with `reroll_one`, will apply at most once even if more than one die is rolled.
    Returns:
        - value: (int) Value of the roll
        - all_rolls ([int]): Values of all dice rolls used in this calculation, in the order they were rolled
    """
    assert not (advantage and disadvantage), "You cannot roll both at advantage and disadvantage"
    assert sides > 0, "Dice must have a nonnegative number of faces. No non-Euclidean geometry"

    if advantage or disadvantage:
        rolls = [randint(1, sides), randint(1, sides)]
        used = [True, True]  # Marking which die values are used

        # Re-roll only one of the dice if a one is rolled
        min_value = min(rolls)
        if (reroll_one and min_value == 1) or (reroll_two and min_value <= 2):
            used[rolls.index(min(rolls))] = False  # Mark a 1 as "unused"

            # Add in a new roll to replace that die
            used.append(True)
            rolls.append(randint(1, sides))

        # Remove the minimum or maximum value, depending on user request
        func = max if advantage else min
        value = func([v for v, u in zip(rolls, used) if u])  # Get the best value of the used dice
        return value, rolls
    else:
        # Simple logic: Not at [dis]advantage
        value = randint(1, sides)
        if (reroll_one and value == 1) or (reroll_two and value <= 2):
            new_value = randint(1, sides)
            return new_value, [new_value, value]
        return value, [value]


class DiceRoll:
    """Representation of a single dice roll.

    Follows the D&D 5e rules for dice. Consult Chapter 7 of the D&D manual for details
    """

    def __init__(self,
                 dice: List[int],
                 modifier: int = 0,
                 reroll_ones: bool = False,
                 reroll_twos: bool = True,
                 advantage: bool = False,
                 disadvantage: bool = False):
        """Roll dice

        Args:
            dice ([int]): List of dice to roll
            modifier (int): Modifier to add to the roll
            reroll_ones (bool): Whether to re-roll dice which are 1 on the first roll
            reroll_twos (bool): Whether to re-roll dice which are 1 or 2 on the first roll
            advantage (bool): Whether to roll each dice twice and take the high value
            disadvantage (bool): Whether to roll the dice twice and take the low value
        """

        assert not (advantage and disadvantage), "You cannot roll both at advantage and disadvantage"
        dice = sorted(dice, reverse=True)  # Sort dice in descending order
        self._dice = Counter(dice)
        self.modifier = modifier
        self.reroll_ones = reroll_ones
        self.reroll_twos = reroll_twos
        self.advantage = advantage
        self.disadvantage = disadvantage

        # Make the rolls. Store the results and all dice which were rolled
        self.results = [roll_die(s, advantage=advantage, disadvantage=disadvantage,
                                 reroll_one=reroll_ones, reroll_two=reroll_twos)
                        for s in self._dice.elements()]

        # Store the result, which is the result of the used dice
        self.value = sum(self.dice_values) + self.modifier

    @property
    def dice_values(self) -> List[int]:
        """Values rolled for each of the dice

        Dice are list in descending order by the number of faces.
        For example, the results from rolling 4d8+2d6 will start
        with all four of the d8's."""
        return [x[0] for x in self.results]

    @property
    def dice(self) -> List[int]:
        """Sizes of the dice that were rolled.

        Dice are listed in descending order by number of faces."""
        return list(self._dice.elements())

    @property
    def raw_rolls(self) -> List[Sequence[int]]:
        return [x[1] for x in self.results]

    @classmethod
    def make_roll(cls, roll: str, reroll_ones: bool = False, reroll_twos: bool = False,
                  advantage: bool = False, disadvantage: bool = False) -> 'DiceRoll':
        """Make a roll given a text string describing the dice

        Args:
            roll (str): String describing the roll, which must not contain spaces
            reroll_ones (bool): Whether to re-roll dice which are 1 on the first roll
            reroll_twos (bool): Whether to re-roll dice which are 1 or 2 on the first roll
            advantage (bool): Whether to roll each dice twice and take the high value
            disadvantage (bool): Whether to roll the dice twice and take the low value
        Returns:
            (DiceRoll) Specified roll
        """

        # Match the dice components
        dice = []
        for match in dice_regex.finditer(roll):
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

        return cls(dice, modifier, reroll_ones=reroll_ones, reroll_twos=reroll_twos,
                   advantage=advantage, disadvantage=disadvantage)

    @property
    def roll_description(self) -> str:
        """Text description of roll.

        Includes the dice that were rolled, the modifier, and any options in plaintext"""
        # Get a description of the dice
        dice_desc = self.dice_description

        # Make a roll description
        desc = ""
        if self.advantage:
            desc = " at advantage"
        elif self.disadvantage:
            desc = " at disadvantage"

        # Mark the re-rolling rules
        if self.reroll_twos:
            desc += " re-rolling twos"
        elif self.reroll_ones:
            desc += " re-rolling ones"
        roll_desc = f'{dice_desc}{desc}'
        return roll_desc

    @property
    def dice_description(self):
        """Description of the dice which were rolled and the modifier"""
        coll_dice = [f'{count}d{sides}' for sides, count in sorted(self._dice.items(), key=lambda x: -x[0])]
        return f'{"+".join(coll_dice)}{self.modifier:+d}'

    def __str__(self):
        return f'{self.roll_description} = {self.value}'
