"""NPC Generator"""
import logging
from random import randint, choice
from typing import Tuple

from modron.config import get_config

logger = logging.getLogger(__name__)

_eye_color = {1: 'blue', 2: 'blue', 3: 'brown', 4: 'brown', 5: 'green', 6: 'grey'}
_hair_color = {1: 'blonde', 2: 'blonde', 3: 'brown', 4: 'brown', 5: 'black', 6: 'redhead/dyed a funky color'}
_tiefling_eye_colors = ['red', 'orange', 'yellow', 'green', 'blue', 'purple', 'black']
_tiefling_horns = ['eyebrow', 'short stubs', 'gazelle', 'rams horns',
                   'malformed/mismatched', 'hooks', 'antlers', 'smooth arc']


config = get_config()


def generate_npc(location='default') -> dict:
    """Randomly-generate an NPC

    Simulates lookup tables based on rolling percentile dice

    Returns:
        (dict): Dictionary describing the NPC
    """

    # Generate major stats
    age, gender = generate_age_and_gender()
    race = generate_race(location)
    output = {
        'race': race,
        'age': age,
        'gender': gender,
        'alignment': generate_alignment(),
        'eyes': _eye_color[randint(1, 6)],
        'hair': _hair_color[randint(1, 6)],
        'skin_tone': randint(1, 6),  # Fitzpatrick scale
        'attractiveness': randint(1, 20),
        'orientation': randint(1, 6),
        'relationship_status': generate_relationship_status(),
    }

    # If race is a tiefling, make a few alterations
    if race == 'tiefling':
        output['hair'] = f'{output["hair"]}, {choice(_tiefling_horns)}'
        output['eyes'] = choice(_tiefling_eye_colors)

    return output


def generate_race(distribution='default') -> str:
    """Randomly select a race from a certain distribution

    Follow's MAB's random generation method which is based on having
    a skewed distribution of common races, where different locations
    may have different distributions of races.

    Args:
        distribution (str): Name of the distribution to pull from
    Returns:
        (str) Name of character race
    """

    # Get the desired location based on the race
    race_dist = config.npc_race_dist[distribution]

    # Make the lookup table
    lookup_table = []
    counter = 0
    for tier_prob, tier_races in zip(config.npc_race_weights, race_dist):
        for race in tier_races:
            counter += tier_prob
            lookup_table.append((counter, race))
    if counter != 100:
        logger.warning('Probability of races does not add up to 100.')

    # Randomly select the probability tier from which to draw a race
    roll = randint(1, counter)
    for threshold, race in lookup_table:
        if roll <= threshold:
            return race
    raise ValueError('Rolling logic broken. Talk to Logan!')


def generate_age_and_gender() -> Tuple[str, str]:
    """Generate the age of an NPC

    Returns:
        - (str) Age range
        - (str) Gender
    """

    roll = randint(1, 100)

    # Determine the gender
    if roll == 100:
        gender = 'male' if randint(1, 2) == 1 else 'female'
    else:
        gender = 'female' if roll % 2 == 0 else 'male'

    # Determine the age
    for threshold, age in config.npc_age_dist:
        if roll <= threshold:
            return age, gender
    raise Exception('Problem with age distribution table. Does it have entries up to 100?')


def generate_relationship_status() -> str:
    """Generate the relationship status for the NPC"""

    roll = randint(1, 20)
    for threshold, status in config.npc_relationship_dist:
        if roll <= threshold:
            return status
    raise Exception('Problem with relationship table. Does it have entries up to 20?')


def generate_alignment() -> str:
    """Generate NPC alignment following Xanathar's distribution"""
    alignment_num = randint(3, 18)

    if alignment_num == 3:
        tie_breaker = randint(1, 2)
        if tie_breaker == 1:
            return 'chaotic evil'
        else:
            return 'chaotic neutral'
    elif alignment_num == 4 or alignment_num == 5:
        return 'lawful evil'
    elif 6 <= alignment_num <= 8:
        return 'neutral evil'
    elif 9 <= alignment_num <= 12:
        return 'neutral'
    elif 13 <= alignment_num <= 15:
        return 'neutral good'
    elif 16 <= alignment_num <= 17:
        tie_breaker = randint(1, 2)
        if tie_breaker == 1:
            return 'lawful good'
        else:
            return 'neutral good'
    else:
        tie_breaker = randint(1, 2)
        if tie_breaker == 1:
            return 'chaotic good'
        else:
            return 'chaotic neutral'
