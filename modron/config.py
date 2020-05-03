""""Configuration details"""
import os

# Dice roll settings
DICE_LOG = 'dice_rolls.csv'
"""Path where Modron should write the result of dice rolls. Set to ``None`` to skip saving"""
DICE_SKIP_CHANNELS = ['bot_test', 'ooc_discussion']
"""Which channels to omit from logging"""

# Character sheet settings
CHARACTER_SHEET_PATH = os.path.join(os.path.dirname(__file__), '..', 'characters')

# NPC Generator Settings
#  Following MAB's NPC generator
RACE_TIER_WEIGHTS = [50, 10, 3, 2]
"""Weights for different probability tiers"""
RACE_DISTRIBUTION = {
    'default': [
        ['human'],
        ['dwarf', 'elf', 'halfling', 'half-orc'],
        ['gnome', 'half-elf'],
        ['dragonborn', 'tiefling']
    ],
    'AAA': [
        ['tiefling'],
        ['dwarf', 'human', 'halfling', 'gnome'],
        ['half-orc', 'half-elf'],
        ['dragonborn', 'elf']
    ]
}
RELATIONSHIP_DIST = [
    (1, 'actively breaking up/single forever'),
    (5, 'bad breakup recently'),
    (10, 'single and fine with it'),
    (14, 'longer relationship'),
    (19, 'married/partnered'),
    (20, 'so in effin\' in love')
]

#  Following Xanathar's
AGE_DISTRIBUTION = [
    (20, '20 years or younger'),
    (60, '21-30 years'),
    (70, '31-40 years'),
    (85, '41-50 years'),
    (95, '51-60 years'),
    (100, '60+ years')
]
