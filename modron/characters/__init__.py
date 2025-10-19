"""Saving and using information about characters"""
from pathlib import Path
from typing import List, Tuple

from modron.characters.base import Character
from modron.characters.dnd import DnD5Character
from modron.config import config


def list_available_characters(guild_id: int, user_id: int) -> List[str]:
    """List the names of character sheets that are available to a user

    Args:
        guild_id: Associated guild
        user_id: ID of the user in question
    Returns:
        List of characters available to this player
    """

    # Return only the sheets for this player
    return [
        s.name[:-4]  # Remove the ".yml"
        for s in config.list_character_sheets(guild_id)
        if Character.from_yaml(s).player == user_id
    ]


def load_character(guild_id: int, name: str) -> Tuple[Character, Path]:
    """Load a character sheet

    Arg:
        guild_id: Associated guild
        name: Name of the character
    Returns:
        - Desired character sheet
        - Absolute path to the character sheet, in case you must save it later
    """
    sheet_path = config.get_character_sheet_path(guild_id, name)
    return DnD5Character.from_yaml(sheet_path), sheet_path.absolute()
