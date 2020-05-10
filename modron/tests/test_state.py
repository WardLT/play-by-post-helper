import os

from modron.db import ModronState
from modron import config


def test_save_and_load():
    # Test that it modifies the file
    before_time = os.path.getmtime(config.STATE_PATH)
    state = ModronState.load()
    state.save()
    after_time = os.path.getmtime(config.STATE_PATH)
    assert after_time > before_time

    # Test that it still loads again
    ModronState.load()
