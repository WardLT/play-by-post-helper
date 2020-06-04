import os
from datetime import datetime

from pytest import fixture

from modron.db import ModronState


@fixture
def state_path(tmpdir):
    state_path = os.path.join(tmpdir, 'state.yml')
    ModronState().save(state_path)
    return state_path


def test_save_and_load(state_path):
    # Modify the file
    state = ModronState.load(state_path)
    state.reminder_time = {'TID': datetime.now()}
    state.save(state_path)

    # Get the changes back
    state = ModronState.load(state_path)
    assert 'TID' in state.reminder_time
