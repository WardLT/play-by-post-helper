from pathlib import Path
from datetime import datetime

from pytest import fixture

from modron.db import ModronState


@fixture
def state_path(tmpdir):
    state_path = Path(tmpdir) / 'state.yml'
    ModronState().save(state_path)
    return state_path


def test_save_and_load(state_path):
    # Modify the file
    state = ModronState.load(state_path)
    state.reminder_time = {1234: datetime.now()}
    state.save(state_path)

    # Get the changes back
    state = ModronState.load(state_path)
    assert 1234 in state.reminder_time


def test_active_character(guild_id, run_in_repo_run, player_id):
    # Make a clean state
    state = ModronState()
    assert state.get_active_character(guild_id, player_id).player == player_id

    # Make sure the character name was stored
    assert state.characters[guild_id][player_id] == 'adrianna'
    assert state.get_active_character(guild_id, player_id).player == player_id
